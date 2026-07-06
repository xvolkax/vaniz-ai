"""CRM adapter interface.

Every provider (Zoho/HubSpot/Salesforce/custom) implements this contract.
The agent never imports a concrete adapter directly — it uses the factory.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from priya.crm.schemas import CRMAppointment, CRMLead, CRMResult, LeadQualification


class CRMAdapter(ABC):
    """Stable vendor-agnostic CRM contract."""

    name: str = "base"

    @abstractmethod
    async def create_lead(self, lead: CRMLead) -> CRMResult:
        ...

    @abstractmethod
    async def update_lead(self, external_id: str, lead: CRMLead) -> CRMResult:
        ...

    @abstractmethod
    async def get_lead(self, phone_number: str) -> CRMLead | None:
        ...

    @abstractmethod
    async def set_qualification(
        self, external_id: str, qualification: LeadQualification, score: int
    ) -> CRMResult:
        ...

    @abstractmethod
    async def add_call_notes(self, external_id: str, notes: str) -> CRMResult:
        ...

    @abstractmethod
    async def create_appointment(self, appointment: CRMAppointment) -> CRMResult:
        ...

    async def aclose(self) -> None:
        return None
