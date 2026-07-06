"""WhatsApp Business Cloud API sender — Phase 2 stub.

Implementation notes for Phase 2:
  * POST https://graph.facebook.com/v20.0/{phone_id}/messages
  * Auth: Bearer permanent token.
  * Use approved message templates for post-call follow-up (24h window rules).
  * Personalize via `components` -> body parameters from FollowUpPayload.
"""
from __future__ import annotations

from priya.whatsapp.base import FollowUpPayload, FollowUpService


class CloudApiFollowUpService(FollowUpService):
    name = "cloud_api"

    def __init__(self, api_key: str, phone_id: str) -> None:
        self.api_key = api_key
        self.phone_id = phone_id

    async def trigger(self, payload: FollowUpPayload) -> bool:  # pragma: no cover
        raise NotImplementedError(
            "WhatsApp Cloud API sender is a Phase 2 stub. Wire graph.facebook.com "
            "template messages here."
        )
