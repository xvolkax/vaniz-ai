"""No-op WhatsApp follow-up (Phase 1 default).

Logs the personalized follow-up payload that WOULD be sent, so the trigger
point is fully wired and audited. Phase 2 replaces this with a real sender.
"""
from __future__ import annotations

from priya.utils.logging import get_logger
from priya.whatsapp.base import FollowUpPayload, FollowUpService

log = get_logger(__name__)


class NoopFollowUpService(FollowUpService):
    name = "noop"

    async def trigger(self, payload: FollowUpPayload) -> bool:
        log.info(
            "whatsapp.noop.follow_up",
            phone=payload.phone_number,
            template=payload.template,
            language=payload.preferred_language,
            next_action=payload.next_action,
        )
        return True
