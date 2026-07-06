"""Render agent knowledge & prompt from the DB (multi-tenant, dynamic).

Replaces the static project.yaml pipeline: builder-level ("Tier 1") facts come
from the `Tenant` row, per-project facts from that tenant's `Property` rows.
Loaded per call (not cached), so dashboard edits are visible on the next call
without restarting the worker.
"""
from __future__ import annotations

import uuid

from priya.db.database import session_scope
from priya.db.models import Property, PropertyType, Tenant
from priya.db.repositories import PropertyRepository, TenantRepository
from priya.utils.logging import get_logger

log = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Tenant resolution
# --------------------------------------------------------------------------- #
async def resolve_tenant(
    *, tenant_id: uuid.UUID | None, dialed_number: str | None, default_slug: str | None
) -> Tenant | None:
    """Pick the tenant for a call: explicit id > dialed number > default slug."""
    async with session_scope() as session:
        repo = TenantRepository(session)
        if tenant_id is not None:
            t = await repo.get(tenant_id)
            if t and t.is_active:
                session.expunge(t)
                return t
        if dialed_number:
            t = await repo.get_by_phone(dialed_number)
            if t:
                session.expunge(t)
                return t
        if default_slug:
            t = await repo.get_by_slug(default_slug)
            if t and t.is_active:
                session.expunge(t)
                return t
    return None


async def load_active_properties(tenant_id: uuid.UUID) -> list[Property]:
    async with session_scope() as session:
        rows = await PropertyRepository(session).list(tenant_id, active_only=True, limit=500)
        for r in rows:
            session.expunge(r)
        return rows


# --------------------------------------------------------------------------- #
# Rendering (mirrors project.loader output shape, sourced from the DB)
# --------------------------------------------------------------------------- #
def _has_plots(props: list[Property]) -> bool:
    return any(p.property_type == PropertyType.plot for p in props)


def _render_property_line(index: int, p: Property) -> str:
    head_meta = ", ".join(x for x in (p.property_type.value, p.location or "") if x)
    head = f"{index}. {p.project_name}"
    if head_meta:
        head = f"{head} — {head_meta}"

    detail: list[str] = []
    for label, val in (
        ("Price", p.price),
        ("Possession", p.possession),
        ("Carpet", p.carpet_area),
        ("RERA", p.rera),
        ("Maintenance", p.maintenance),
        ("Parking", p.parking),
        ("Status", p.construction_status),
        ("Road", p.road_width),
    ):
        if val:
            detail.append(f"{label}: {val}")
    if p.amenities:
        detail.append(f"Amenities: {', '.join(p.amenities)}")
    if p.connectivity:
        detail.append(f"Connectivity: {p.connectivity}")

    body = " ".join(f"{d}." for d in detail)
    return f"{head}. {body}".strip()


def _render_shared(t: Tenant, props: list[Property]) -> list[str]:
    lines: list[str] = []
    extra = t.knowledge_extra or {}

    if t.builder_name:
        desc = f" — {t.builder_description}" if t.builder_description else ""
        lines.append(f"Builder: {t.builder_name}{desc}")

    cred = [x for x in (
        f"{t.years_in_business} experience" if t.years_in_business else "",
        t.completed_projects or "",
        t.track_record or "",
    ) if x]
    if cred:
        lines.append("Track record: " + "; ".join(cred) + ".")
    if t.penalty_clause:
        lines.append(f"Delay/penalty: {t.penalty_clause}.")

    fin = []
    if t.loan_banks:
        fin.append(f"Loan approved by {', '.join(t.loan_banks)}")
    if t.emi_estimate:
        fin.append(f"EMI example: {t.emi_estimate}")
    if fin:
        lines.append("Home loan: " + ". ".join(fin) + ".")

    cb = extra.get("cost_breakup") or {}
    parts = [cb.get("gst"), cb.get("stamp_duty_registration"), cb.get("hidden_charges")]
    parts = [x for x in parts if x]
    if parts:
        lines.append("Charges & taxes: " + " ".join(f"{x}." for x in parts))

    lg = extra.get("legal") or {}
    parts = [lg.get("title"), lg.get("approvals"), lg.get("oc_cc")]
    parts = [x for x in parts if x]
    if parts:
        lines.append("Legal: " + " ".join(f"{x}." for x in parts))

    pi = extra.get("plot_info") or {}
    if pi and _has_plots(props):
        parts = [pi.get("registry"), pi.get("mutation"), pi.get("land_use"), pi.get("govt_approval")]
        parts = [x for x in parts if x]
        if parts:
            lines.append("Plots (registry/legal): " + " ".join(f"{x}." for x in parts))

    if extra.get("market_note"):
        lines.append(f"Investment/appreciation: {extra['market_note']}.")

    contact = t.site_visit_contact or t.whatsapp_number
    if contact:
        lines.append(f"Site visit / WhatsApp: {contact}.")
    if t.brochure_available:
        lines.append("Brochure: available to send on WhatsApp.")

    return lines


def render_tenant_knowledge(t: Tenant, props: list[Property]) -> str:
    """Compact fact block: Tier-1 shared blocks + the property catalog."""
    lines: list[str] = _render_shared(t, props)
    if t.region:
        lines.insert(1 if t.builder_name else 0, f"Region: {t.region}")

    lines.append("")
    lines.append(
        "Projects (answer ONLY from this list; never invent a project, price or detail):"
    )
    if props:
        for i, p in enumerate(props, 1):
            lines.append(_render_property_line(i, p))
    else:
        lines.append("(No active projects configured yet.)")

    return "\n".join(lines)
