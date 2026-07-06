"""Outbound calling via Vobiz SIP.

Places an outbound call: creates a room, dispatches the Priya agent, then dials
the destination number through the Vobiz outbound trunk as a SIP participant.
"""
from __future__ import annotations

import json
import uuid

from livekit import api

from priya.config import settings
from priya.utils.logging import get_logger

log = get_logger(__name__)


def _client() -> api.LiveKitAPI:
    return api.LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )


async def place_outbound_call(
    phone_number: str,
    lead_name: str | None = None,
    tenant_id: str | None = None,
    campaign_id: str | None = None,
) -> dict:
    """Dial `phone_number` and connect the Priya agent. Returns room + status."""
    if not settings.sip_outbound_trunk_id:
        raise RuntimeError("SIP_OUTBOUND_TRUNK_ID not configured. Run scripts/setup_sip.py.")

    room_name = f"priya-out-{uuid.uuid4().hex[:12]}"
    metadata = json.dumps(
        {
            "direction": "outbound",
            "phone_number": phone_number,
            "lead_name": lead_name,
            "tenant_id": tenant_id,
            "campaign_id": campaign_id,
        }
    )

    lk = _client()
    try:
        # 1) Explicitly dispatch the agent into the room first.
        await lk.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=settings.agent_name,
                room=room_name,
                metadata=metadata,
            )
        )

        # 2) Dial the callee via the Vobiz outbound trunk.
        sip_participant = await lk.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=settings.sip_outbound_trunk_id,
                sip_call_to=phone_number,
                room_name=room_name,
                participant_identity=f"sip-{phone_number}",
                participant_name=lead_name or phone_number,
                participant_metadata=metadata,
                wait_until_answered=True,
            )
        )
        log.info(
            "outbound.call.placed",
            room=room_name,
            phone=phone_number,
            participant=sip_participant.participant_id,
        )
        return {
            "room_name": room_name,
            "phone_number": phone_number,
            "participant_id": sip_participant.participant_id,
            "status": "dialing",
        }
    finally:
        await lk.aclose()
