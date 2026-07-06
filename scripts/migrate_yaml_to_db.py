#!/usr/bin/env python
"""One-time migration: project.yaml  ->  DB (Tenant + Properties + owner User).

Reads the packaged (or PROJECT_DATA_PATH) catalog and seeds a single tenant so
the SaaS/DB knowledge path can serve the same content the YAML used to.

Usage:
    python scripts/migrate_yaml_to_db.py --slug patna-realty \
        --owner-email owner@patna.com --owner-password "changeme123" \
        [--phone +919886012345]

Idempotent by tenant slug: re-running updates the tenant's Tier-1 facts and
adds any missing properties (matched by slug).
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from priya.auth.security import hash_password  # noqa: E402
from priya.db.database import init_db, session_scope  # noqa: E402
from priya.db.models import PropertyType, UserRole  # noqa: E402
from priya.db.repositories import (  # noqa: E402
    PropertyRepository,
    TenantRepository,
    UserRepository,
)
from priya.project.loader import get_project  # noqa: E402

_LAKH = 10**5
_CRORE = 10**7


def _parse_price_min(price: str | None) -> float | None:
    """Best-effort extraction of the lowest INR figure from a price string."""
    if not price:
        return None
    low = price.lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(lakh|crore|cr)", low)
    if not m:
        m2 = re.search(r"(\d[\d,]*)\s*rupaye", low)
        if m2:
            return float(m2.group(1).replace(",", ""))
        return None
    val = float(m.group(1))
    unit = m.group(2)
    return val * (_CRORE if unit in ("crore", "cr") else _LAKH)


def _property_type(raw: str) -> PropertyType:
    try:
        return PropertyType(raw.strip().lower())
    except ValueError:
        return PropertyType.other


async def migrate(slug: str, owner_email: str, owner_password: str, phone: str | None) -> None:
    p = get_project()
    await init_db()

    async with session_scope() as session:
        tenants = TenantRepository(session)
        users = UserRepository(session)
        props = PropertyRepository(session)

        tenant = await tenants.get_by_slug(slug)
        tier1 = dict(
            name=p.builder_name or slug,
            builder_name=p.builder_name or None,
            builder_description=p.builder_description or None,
            region=p.region or None,
            years_in_business=p.years_in_business or None,
            completed_projects=p.completed_projects or None,
            track_record=p.track_record or None,
            penalty_clause=p.penalty_clause or None,
            site_visit_contact=p.site_visit_contact or None,
            whatsapp_number=p.whatsapp_number or None,
            brochure_available=p.brochure_available,
            loan_banks=p.loan_banks,
            emi_estimate=p.emi_estimate or None,
            phone_number=phone,
            knowledge_extra={
                "cost_breakup": p.cost_breakup,
                "legal": p.legal,
                "plot_info": p.plot_info,
                "market_note": p.market_note,
            },
        )

        if tenant is None:
            tenant = await tenants.create(slug=slug, **tier1)
            print(f"created tenant {slug} ({tenant.id})")
        else:
            await tenants.update(tenant.id, **tier1)
            print(f"updated tenant {slug} ({tenant.id})")

        # Owner user
        if await users.get_by_email(owner_email) is None:
            await users.create(
                tenant_id=tenant.id,
                email=owner_email,
                hashed_password=hash_password(owner_password),
                full_name="Owner",
                role=UserRole.owner,
            )
            print(f"created owner user {owner_email}")
        else:
            print(f"owner user {owner_email} already exists — skipping")

        # Properties (match existing by slug to stay idempotent)
        existing = {pr.slug for pr in await props.list(tenant.id, limit=500) if pr.slug}
        added = 0
        for proj in p.projects:
            if proj.id and proj.id in existing:
                continue
            await props.create(
                tenant_id=tenant.id,
                slug=proj.id or None,
                project_name=proj.project_name,
                property_type=_property_type(proj.property_type),
                location=proj.location or None,
                price=proj.price or None,
                total_cost=proj.total_cost or None,
                possession=proj.possession or None,
                carpet_area=proj.carpet_area or None,
                parking=proj.parking or None,
                maintenance=proj.maintenance or None,
                construction_status=proj.construction_status or None,
                rera=proj.rera or None,
                connectivity=proj.connectivity or None,
                road_width=proj.road_width or None,
                amenities=proj.amenities,
                price_min=_parse_price_min(proj.price),
            )
            added += 1
        print(f"added {added} properties ({len(p.projects)} in YAML)")

    print("migration complete.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Migrate project.yaml into the DB.")
    ap.add_argument("--slug", required=True, help="Tenant slug, e.g. patna-realty")
    ap.add_argument("--owner-email", required=True)
    ap.add_argument("--owner-password", required=True)
    ap.add_argument("--phone", default=None, help="Tenant inbound DID (E.164)")
    args = ap.parse_args()
    asyncio.run(
        migrate(args.slug, args.owner_email, args.owner_password, args.phone)
    )


if __name__ == "__main__":
    main()
