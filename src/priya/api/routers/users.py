"""User management within a tenant (admin/owner only).

All operations are scoped to the caller's tenant_id from the JWT. A user in
tenant A can never see or modify users in tenant B.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from priya.api.schemas import UserCreate, UserResponse, UserUpdate
from priya.auth.dependencies import CurrentUser, get_db, require_role
from priya.auth.security import hash_password
from priya.db.models import UserRole
from priya.db.repositories import UserRepository
from priya.utils.logging import get_logger

router = APIRouter(prefix="/users", tags=["users"])
log = get_logger(__name__)


@router.get("", response_model=list[UserResponse])
async def list_users(
    user: CurrentUser = Depends(require_role(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    rows = await UserRepository(session).list_for_tenant(user.tenant_id)
    return [UserResponse.model_validate(r) for r in rows]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    user: CurrentUser = Depends(require_role(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(session)
    if await repo.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    # Only an owner may create another owner.
    if payload.role == UserRole.owner and user.role != UserRole.owner:
        raise HTTPException(status_code=403, detail="Only an owner can create owners")
    row = await repo.create(
        tenant_id=user.tenant_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    log.info("users.create", tenant=str(user.tenant_id), email=row.email, role=row.role.value)
    return UserResponse.model_validate(row)


async def _get_scoped_user(repo: UserRepository, user_id: uuid.UUID, tenant_id: uuid.UUID):
    row = await repo.get(user_id)
    if row is None or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    return row


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    user: CurrentUser = Depends(require_role(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(session)
    target = await _get_scoped_user(repo, user_id, user.tenant_id)

    fields = payload.model_dump(exclude_unset=True)
    if "password" in fields and fields["password"]:
        fields["hashed_password"] = hash_password(fields.pop("password"))
    else:
        fields.pop("password", None)
    if fields.get("role") == UserRole.owner and user.role != UserRole.owner:
        raise HTTPException(status_code=403, detail="Only an owner can grant owner role")

    row = await repo.update(target.id, **fields)
    return UserResponse.model_validate(row)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    user: CurrentUser = Depends(require_role(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> None:
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    repo = UserRepository(session)
    await _get_scoped_user(repo, user_id, user.tenant_id)
    await repo.delete(user_id)
    log.info("users.delete", tenant=str(user.tenant_id), user_id=str(user_id))
