"""WhatsApp follow-up service factory."""
from __future__ import annotations

from functools import lru_cache

from priya.config import settings
from priya.utils.logging import get_logger
from priya.whatsapp.base import FollowUpService
from priya.whatsapp.noop import NoopFollowUpService

log = get_logger(__name__)


@lru_cache(maxsize=1)
def get_follow_up_service() -> FollowUpService:
    provider = settings.whatsapp_provider.lower()
    if provider == "noop":
        return NoopFollowUpService()
    if provider == "cloud_api":
        from priya.whatsapp.cloud_api import CloudApiFollowUpService

        return CloudApiFollowUpService(
            api_key=settings.whatsapp_api_key, phone_id=settings.whatsapp_phone_id
        )
    log.warning("whatsapp.factory.unknown_provider", provider=provider)
    return NoopFollowUpService()
