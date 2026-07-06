"""Password hashing (bcrypt) and JWT token issuance / verification.

Uses `bcrypt` directly (no passlib) to avoid the well-known passlib/bcrypt 4.x
version-detection warnings, and PyJWT for token signing.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from priya.config import settings

_BCRYPT_ROUNDS = 12


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #
def hash_password(plain: str) -> str:
    """Return a bcrypt hash of `plain` (utf-8, salted)."""
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time verify of `plain` against a stored bcrypt `hashed`."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- #
# JWT
# --------------------------------------------------------------------------- #
def create_access_token(
    *,
    user_id: uuid.UUID | str,
    tenant_id: uuid.UUID | str,
    role: str,
    email: str,
    expires_minutes: int | None = None,
) -> str:
    """Sign a JWT access token embedding tenant + role for RBAC/isolation."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes or settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode & verify a JWT. Raises jwt.PyJWTError on any failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
