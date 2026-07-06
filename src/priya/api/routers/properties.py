"""Property CRUD — the dashboard-managed catalog the AI reads at call time.

Every operation is tenant-scoped via the JWT. Properties created/edited here
become available to the voice agent on the NEXT call (no restart), replacing
the static project.yaml.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from priya.api.schemas import PropertyCreate, PropertyResponse, PropertyUpdate
from priya.auth.dependencies import CurrentUser, get_current_user, get_db, require_role
from priya.db.models import UserRole
from priya.db.repositories import PropertyRepository
from priya.utils.logging import get_logger

router = APIRouter(prefix="/properties", tags=["properties"])
log = get_logger(__name__)


@router.get("", response_model=list[PropertyResponse])
async def list_properties(
    active_only: bool = Query(default=False),
    limit: int = Query(default=200, le=500),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[PropertyResponse]:
    rows = await PropertyRepository(session).list(
        user.tenant_id, active_only=active_only, limit=limit, offset=offset
    )
    return [PropertyResponse.model_validate(r) for r in rows]


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    payload: PropertyCreate,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    row = await PropertyRepository(session).create(
        tenant_id=user.tenant_id, **payload.model_dump()
    )
    log.info("properties.create", tenant=str(user.tenant_id), name=row.project_name)
    return PropertyResponse.model_validate(row)


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    row = await PropertyRepository(session).get(property_id, tenant_id=user.tenant_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return PropertyResponse.model_validate(row)


@router.patch("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: uuid.UUID,
    payload: PropertyUpdate,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    repo = PropertyRepository(session)
    existing = await repo.get(property_id, tenant_id=user.tenant_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Property not found")
    fields = payload.model_dump(exclude_unset=True)
    row = await repo.update(property_id, **fields)
    log.info("properties.update", tenant=str(user.tenant_id), id=str(property_id))
    return PropertyResponse.model_validate(row)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: uuid.UUID,
    user: CurrentUser = Depends(require_role(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> None:
    repo = PropertyRepository(session)
    existing = await repo.get(property_id, tenant_id=user.tenant_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Property not found")
    await repo.delete(property_id)
    log.info("properties.delete", tenant=str(user.tenant_id), id=str(property_id))
