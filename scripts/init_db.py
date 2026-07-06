#!/usr/bin/env python
"""Bootstrap database tables (dev convenience).

Production should use Alembic migrations (`alembic upgrade head`). This is handy
for local development and CI.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from priya.db.database import dispose_db, init_db  # noqa: E402


async def main() -> None:
    await init_db()
    await dispose_db()
    print("Database tables created.")


if __name__ == "__main__":
    asyncio.run(main())
