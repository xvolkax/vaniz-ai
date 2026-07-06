"""WhatsApp follow-up interface + payload contract."""
from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class FollowUpPayload(BaseModel):
    """Data handed to the WhatsApp automation layer after a call ends."""

    phone_number: str
    name: str | None = None
    preferred_language: str = "hi"
    qualification: str | None = None
    property_type: str | None = None
    preferred_location: str | None = None
    budget_summary: str | None = None
    next_action: str | None = None
    appointment_time: str | None = None
    template: str = "post_call_followup"
    variables: dict = Field(default_factory=dict)


class FollowUpService(ABC):
    """Contract for triggering post-call WhatsApp follow-ups."""

    name: str = "base"

    @abstractmethod
    async def trigger(self, payload: FollowUpPayload) -> bool:
        """Enqueue / send a personalized follow-up message. Returns success."""

    async def aclose(self) -> None:
        return None
