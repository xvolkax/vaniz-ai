#!/usr/bin/env python
"""Provision Vobiz SIP trunks + dispatch rule on LiveKit.

Run once after configuring LiveKit + Vobiz credentials in `.env`:

    python scripts/setup_sip.py

Copy the printed IDs into your `.env` (SIP_INBOUND_TRUNK_ID, etc.).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from priya.telephony.sip import provision  # noqa: E402


async def main() -> None:
    result = await provision()
    print("\n=== SIP provisioning complete — add these to .env ===\n")
    print(f"SIP_INBOUND_TRUNK_ID={result.inbound_trunk_id}")
    print(f"SIP_OUTBOUND_TRUNK_ID={result.outbound_trunk_id}")
    print(f"SIP_DISPATCH_RULE_ID={result.dispatch_rule_id}")
    print("\nInbound calls to your Vobiz number will now reach Priya.\n")


if __name__ == "__main__":
    asyncio.run(main())
