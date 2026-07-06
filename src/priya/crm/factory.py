"""CRM adapter factory — selects implementation from CRM_PROVIDER."""
from __future__ import annotations

from functools import lru_cache

from priya.config import settings
from priya.crm.base import CRMAdapter
from priya.crm.noop import NoopCRMAdapter
from priya.utils.logging import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def get_crm_adapter() -> CRMAdapter:
    provider = settings.crm_provider.lower()
    if provider == "noop":
        return NoopCRMAdapter()
    if provider == "zoho":
        from priya.crm.zoho import ZohoCRMAdapter

        return ZohoCRMAdapter(api_key=settings.crm_api_key, base_url=settings.crm_base_url)
    if provider == "hubspot":
        from priya.crm.hubspot import HubSpotCRMAdapter

        return HubSpotCRMAdapter(api_key=settings.crm_api_key)
    if provider == "salesforce":
        from priya.crm.salesforce import SalesforceCRMAdapter

        return SalesforceCRMAdapter(api_key=settings.crm_api_key, base_url=settings.crm_base_url)
    log.warning("crm.factory.unknown_provider", provider=provider)
    return NoopCRMAdapter()
