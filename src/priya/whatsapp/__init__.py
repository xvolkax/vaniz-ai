"""WhatsApp follow-up package — Phase 2 interfaces.

Defines the follow-up trigger contract used after call completion. Phase 1 uses
a NoopFollowUp that logs the intended payload; Phase 2 swaps in a real
WhatsApp Business API / Gupshup / Twilio sender behind the same interface.
"""
from priya.whatsapp.base import FollowUpService, FollowUpPayload
from priya.whatsapp.factory import get_follow_up_service

__all__ = ["FollowUpService", "FollowUpPayload", "get_follow_up_service"]
