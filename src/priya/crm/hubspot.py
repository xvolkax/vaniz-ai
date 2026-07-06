"""HubSpot CRM adapter — Phase 2 stub.

Implementation notes for Phase 2:
  * Auth: Private App token (Bearer) or OAuth2.
  * Endpoints: POST /crm/v3/objects/contacts, PATCH .../{id}, search API.
  * Map CRMLead -> contact properties (firstname, phone, city, custom props).
"""
from __future__ import annotations

from priya.crm.base import CRMAdapter
from priya.crm.schemas import CRMAppointment, CRMLead, CRMResult, LeadQualification


class HubSpotCRMAdapter(CRMAdapter):
    name = "hubspot"

    def __init__(self, api_key: str, base_url: str = "https://api.hubapi.com") -> None:
        self.api_key = api_key
        self.base_url = base_url

    async def create_lead(self, lead: CRMLead) -> CRMResult:
        raise NotImplementedError("HubSpot adapter is a Phase 2 stub.")

    async def update_lead(self, external_id: str, lead: CRMLead) -> CRMResult:
        raise NotImplementedError("HubSpot adapter is a Phase 2 stub.")

    async def get_lead(self, phone_number: str) -> CRMLead | None:
        raise NotImplementedError("HubSpot adapter is a Phase 2 stub.")

    async def set_qualification(
        self, external_id: str, qualification: LeadQualification, score: int
    ) -> CRMResult:
        raise NotImplementedError("HubSpot adapter is a Phase 2 stub.")

    async def add_call_notes(self, external_id: str, notes: str) -> CRMResult:
        raise NotImplementedError("HubSpot adapter is a Phase 2 stub.")

    async def create_appointment(self, appointment: CRMAppointment) -> CRMResult:
        raise NotImplementedError("HubSpot adapter is a Phase 2 stub.")
