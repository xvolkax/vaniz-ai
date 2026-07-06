"""Authentication & authorization for the SaaS control-plane.

JWT-based auth with bcrypt password hashing. Every authenticated request is
scoped to a single tenant (multi-tenant data isolation) and carries a role for
RBAC checks.
"""
from __future__ import annotations

from priya.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

__all__ = [
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
]
