"""Vobiz <-> LiveKit SIP provisioning.

Creates (idempotently) the inbound trunk, outbound trunk and dispatch rule that
route Vobiz virtual-number calls to the Priya agent. Run once via
`scripts/setup_sip.py`; the returned IDs go into `.env`.

Docs model (LiveKit SIP):
  * Inbound trunk  : accepts calls from Vobiz to your LiveKit number.
  * Outbound trunk : lets LiveKit place calls out via Vobiz.
  * Dispatch rule  : maps inbound calls -> a room + auto-dispatches the agent.
"""
from __future__ import annotations

from dataclasses import dataclass

from livekit import api

from priya.config import settings
from priya.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class SIPProvisionResult:
    inbound_trunk_id: str
    outbound_trunk_id: str
    dispatch_rule_id: str


def _client() -> api.LiveKitAPI:
    return api.LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )


async def create_inbound_trunk(lk: api.LiveKitAPI) -> str:
    trunk = api.SIPInboundTrunkInfo(
        name="vobiz-inbound",
        numbers=[settings.vobiz_phone_number],
        # Restrict to Vobiz signalling IPs in production for security.
        allowed_addresses=[],
        auth_username=settings.vobiz_sip_username,
        auth_password=settings.vobiz_sip_password,
    )
    resp = await lk.sip.create_inbound_trunk(
        api.CreateSIPInboundTrunkRequest(trunk=trunk)
    )
    log.info("sip.inbound_trunk.created", trunk_id=resp.sip_trunk_id)
    return resp.sip_trunk_id


async def create_outbound_trunk(lk: api.LiveKitAPI) -> str:
    trunk = api.SIPOutboundTrunkInfo(
        name="vobiz-outbound",
        address=f"{settings.vobiz_sip_host}:{settings.vobiz_sip_port}",
        transport=api.SIPTransport.SIP_TRANSPORT_AUTO,
        numbers=[settings.vobiz_phone_number],
        auth_username=settings.vobiz_sip_username,
        auth_password=settings.vobiz_sip_password,
    )
    resp = await lk.sip.create_outbound_trunk(
        api.CreateSIPOutboundTrunkRequest(trunk=trunk)
    )
    log.info("sip.outbound_trunk.created", trunk_id=resp.sip_trunk_id)
    return resp.sip_trunk_id


async def create_dispatch_rule(lk: api.LiveKitAPI, inbound_trunk_id: str) -> str:
    """Inbound calls -> unique room, auto-dispatch the Priya agent into it."""
    rule = api.SIPDispatchRule(
        dispatch_rule_individual=api.SIPDispatchRuleIndividual(room_prefix="priya-call-")
    )
    request = api.CreateSIPDispatchRuleRequest(
        rule=rule,
        trunk_ids=[inbound_trunk_id],
        room_config=api.RoomConfiguration(
            agents=[api.RoomAgentDispatch(agent_name=settings.agent_name)]
        ),
    )
    resp = await lk.sip.create_dispatch_rule(request)
    log.info("sip.dispatch_rule.created", rule_id=resp.sip_dispatch_rule_id)
    return resp.sip_dispatch_rule_id


async def provision() -> SIPProvisionResult:
    lk = _client()
    try:
        inbound = await create_inbound_trunk(lk)
        outbound = await create_outbound_trunk(lk)
        rule = await create_dispatch_rule(lk, inbound)
        return SIPProvisionResult(
            inbound_trunk_id=inbound,
            outbound_trunk_id=outbound,
            dispatch_rule_id=rule,
        )
    finally:
        await lk.aclose()
