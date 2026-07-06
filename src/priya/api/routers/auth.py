"""Authentication endpoints: tenant signup, login, current-user.

- POST /auth/register  : create a tenant + its first owner user (public signup,
  gated by ALLOW_PUBLIC_SIGNUP).
- POST /auth/login     : exchange email/password for a JWT access token.
- GET  /auth/me        : return the authenticated user profile.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from priya.api.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from priya.auth.dependencies import CurrentUser, get_current_user, get_db
from priya.auth.security import create_access_token, hash_password, verify_password
from priya.config import settings
from priya.db.models import UserRole
from priya.db.repositories import TenantRepository, UserRepository
from priya.utils.logging import get_logger

router = APIRouter(prefix="/auth", tags=["auth"])
log = get_logger(__name__)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    if not settings.allow_public_signup:
        raise HTTPException(status_code=403, detail="Public signup is disabled")

    tenants = TenantRepository(session)
    users = UserRepository(session)

    if await tenants.get_by_slug(payload.tenant_slug):
        raise HTTPException(status_code=409, detail="Tenant slug already taken")
    if await users.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant = await tenants.create(name=payload.tenant_name, slug=payload.tenant_slug)
    user = await users.create(
        tenant_id=tenant.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.owner,
    )
    log.info("auth.register", tenant=tenant.slug, user=user.email)

    token = create_access_token(
        user_id=user.id, tenant_id=tenant.id, role=user.role.value, email=user.email
    )
    return TokenResponse(
        access_token=token, expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    users = UserRepository(session)
    user = await users.get_by_email(payload.email)
    # Uniform error + always run a hash compare path to reduce user enumeration.
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        user_id=user.id, tenant_id=user.tenant_id, role=user.role.value, email=user.email
    )
    log.info("auth.login", user=user.email)
    return TokenResponse(
        access_token=token, expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.get("/me", response_model=UserResponse)
async def me(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    row = await UserRepository(session).get(user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(row)
