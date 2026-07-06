#!/usr/bin/env python
"""Trigger a single outbound call from the CLI.

    python scripts/call_outbound.py +9198XXXXXXXX "Rahul Sharma"
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from priya.telephony.outbound import place_outbound_call  # noqa: E402


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/call_outbound.py <phone_e164> [name]")
        raise SystemExit(1)
    phone = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else None
    result = await place_outbound_call(phone, name)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
