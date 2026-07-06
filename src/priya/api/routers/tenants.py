"""Tenant (broker/organization) self-service endpoints.

A user can only read/update their OWN tenant — the tenant_id comes from the JWT,
never from the client, guaranteeing isolation.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from priya.api.schemas import TenantResponse, TenantUpdate
from priya.auth.dependencies import CurrentUser, get_current_user, get_db, require_role
from priya.db.models import UserRole
from priya.db.repositories import TenantRepository

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenantResponse:
    tenant = await TenantRepository(session).get(user.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)


@router.patch("/me", response_model=TenantResponse)
async def update_my_tenant(
    payload: TenantUpdate,
    user: CurrentUser = Depends(require_role(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> TenantResponse:
    fields = payload.model_dump(exclude_unset=True)
    tenant = await TenantRepository(session).update(user.tenant_id, **fields)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)
