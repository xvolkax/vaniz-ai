"""No-op CRM adapter (Phase 1 default).

Persists nothing to an external CRM — our own PostgreSQL is the system of
record in Phase 1. It logs the sync intent for auditability so that when a real
CRM is enabled in Phase 2, the exact same call sites work unchanged.
"""
from __future__ import annotations

from priya.crm.base import CRMAdapter
from priya.crm.schemas import CRMAppointment, CRMLead, CRMResult, LeadQualification
from priya.utils.logging import get_logger

log = get_logger(__name__)


class NoopCRMAdapter(CRMAdapter):
    name = "noop"

    async def create_lead(self, lead: CRMLead) -> CRMResult:
        log.info("crm.noop.create_lead", phone=lead.phone_number)
        return CRMResult(success=True, external_id=None, message="stored in local DB only")

    async def update_lead(self, external_id: str, lead: CRMLead) -> CRMResult:
        log.info("crm.noop.update_lead", external_id=external_id)
        return CRMResult(success=True, external_id=external_id)

    async def get_lead(self, phone_number: str) -> CRMLead | None:
        return None

    async def set_qualification(
        self, external_id: str, qualification: LeadQualification, score: int
    ) -> CRMResult:
        log.info("crm.noop.qualification", external_id=external_id, q=qualification, score=score)
        return CRMResult(success=True, external_id=external_id)

    async def add_call_notes(self, external_id: str, notes: str) -> CRMResult:
        log.info("crm.noop.notes", external_id=external_id)
        return CRMResult(success=True, external_id=external_id)

    async def create_appointment(self, appointment: CRMAppointment) -> CRMResult:
        log.info("crm.noop.appointment", type=appointment.type)
        return CRMResult(success=True)
