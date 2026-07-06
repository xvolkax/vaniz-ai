"""Zoho CRM adapter — Phase 2 stub.

Implementation notes for Phase 2:
  * Auth: OAuth2 refresh-token flow -> access token cached in memory/Redis.
  * Endpoints: POST /crm/v5/Leads, PUT /crm/v5/Leads/{id}, GET with criteria.
  * Map CRMLead -> Zoho Lead fields (Last_Name, Phone, City, custom fields).
  * Rate limits: respect Zoho API credit limits with tenacity backoff.
"""
from __future__ import annotations

from priya.crm.base import CRMAdapter
from priya.crm.schemas import CRMAppointment, CRMLead, CRMResult, LeadQualification


class ZohoCRMAdapter(CRMAdapter):
    name = "zoho"

    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url

    async def create_lead(self, lead: CRMLead) -> CRMResult:
        raise NotImplementedError("Zoho adapter is a Phase 2 stub.")

    async def update_lead(self, external_id: str, lead: CRMLead) -> CRMResult:
        raise NotImplementedError("Zoho adapter is a Phase 2 stub.")

    async def get_lead(self, phone_number: str) -> CRMLead | None:
        raise NotImplementedError("Zoho adapter is a Phase 2 stub.")

    async def set_qualification(
        self, external_id: str, qualification: LeadQualification, score: int
    ) -> CRMResult:
        raise NotImplementedError("Zoho adapter is a Phase 2 stub.")

    async def add_call_notes(self, external_id: str, notes: str) -> CRMResult:
        raise NotImplementedError("Zoho adapter is a Phase 2 stub.")

    async def create_appointment(self, appointment: CRMAppointment) -> CRMResult:
        raise NotImplementedError("Zoho adapter is a Phase 2 stub.")
