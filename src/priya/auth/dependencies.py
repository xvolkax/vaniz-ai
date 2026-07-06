"""FastAPI dependencies: DB session, current user, tenant scope, RBAC.

Every protected route depends on `get_current_user`, which decodes the JWT,
loads the user, and guarantees the request is bound to an active tenant. Role
checks are composed via `require_role(...)`.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from priya.auth.security import decode_access_token
from priya.db.database import get_sessionmaker
from priya.db.models import User, UserRole
from priya.db.repositories import UserRepository

_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional DB session (commit on success, rollback on error)."""
    maker = get_sessionmaker()
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@dataclass(slots=True)
class CurrentUser:
    """Authenticated principal for the request, always tenant-scoped."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: UserRole
    full_name: str | None = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")

    user: User | None = await UserRepository(session).get(uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

    return CurrentUser(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
    )


# --------------------------------------------------------------------------- #
# Role-based access control
# --------------------------------------------------------------------------- #
_ROLE_RANK = {
    UserRole.viewer: 0,
    UserRole.agent: 1,
    UserRole.admin: 2,
    UserRole.owner: 3,
}


def require_role(minimum: UserRole):
    """Dependency factory enforcing a minimum role (hierarchical)."""

    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if _ROLE_RANK[user.role] < _ROLE_RANK[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum.value} role or higher",
            )
        return user

    return _checker
