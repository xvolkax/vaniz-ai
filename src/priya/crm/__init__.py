"""CRM integration package — vendor-agnostic adapter pattern.

The agent depends only on the `CRMAdapter` interface. Concrete adapters for
Zoho / HubSpot / Salesforce are Phase 2 stubs. Selection is driven by
CRM_PROVIDER env var.
"""
from priya.crm.base import CRMAdapter
from priya.crm.factory import get_crm_adapter
from priya.crm.schemas import CRMAppointment, CRMLead, LeadQualification

__all__ = [
    "CRMAdapter",
    "CRMLead",
    "CRMAppointment",
    "LeadQualification",
    "get_crm_adapter",
]
