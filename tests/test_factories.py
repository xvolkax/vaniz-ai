"""Tests for pluggable adapter factories + API schema validation."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from priya.api.schemas import OutboundCallRequest
from priya.crm.factory import get_crm_adapter
from priya.crm.noop import NoopCRMAdapter
from priya.whatsapp.factory import get_follow_up_service
from priya.whatsapp.noop import NoopFollowUpService


def test_default_crm_is_noop() -> None:
    assert isinstance(get_crm_adapter(), NoopCRMAdapter)


def test_default_whatsapp_is_noop() -> None:
    assert isinstance(get_follow_up_service(), NoopFollowUpService)


async def test_noop_crm_create_lead() -> None:
    from priya.crm.schemas import CRMLead

    result = await NoopCRMAdapter().create_lead(CRMLead(phone_number="+919812345678"))
    assert result.success is True


def test_outbound_request_valid_phone() -> None:
    req = OutboundCallRequest(phone_number="+919812345678", lead_name="Rahul")
    assert req.phone_number == "+919812345678"


def test_outbound_request_invalid_phone() -> None:
    with pytest.raises(ValidationError):
        OutboundCallRequest(phone_number="not-a-number")
