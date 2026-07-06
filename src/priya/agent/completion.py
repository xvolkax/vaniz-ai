"""Call completion: summary generation, persistence, WhatsApp follow-up.

`finalize_call` is idempotent and invoked both by the `finalize_call` tool and
the worker's shutdown callback, so a summary is always produced even if the
caller hangs up abruptly.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from priya.agent.context import CallContext
from priya.agent.state import LeadProfile
from priya.analytics import metrics as m
from priya.config import settings
from priya.db.database import session_scope
from priya.db.models import CallOutcome, LeadSource, LeadStatus
from priya.db.repositories import (
    AuditRepository,
    CallRepository,
    CampaignRepository,
    LeadRepository,
    SummaryRepository,
)
from priya.utils.logging import get_logger
from priya.whatsapp.base import FollowUpPayload

log = get_logger(__name__)


def _format_budget(lead: LeadProfile) -> str | None:
    def fmt(v: float | None) -> str | None:
        if v is None:
            return None
        if v >= 1e7:
            num = f"{v / 1e7:.2f}".rstrip("0").rstrip(".")
            return f"{num} Cr"
        return f"{v / 1e5:.0f} L"

    lo, hi = fmt(lead.budget_min), fmt(lead.budget_max)
    if lo and hi:
        return f"{lo} - {hi}"
    return hi or lo


def _recommended_next_action(lead: LeadProfile) -> str:
    if lead.interested is False:
        return "Mark as not interested. No immediate follow-up."
    if lead.site_visit_interest:
        return "Confirm site visit; send location + agent details on WhatsApp."
    band = lead.qualification_band()
    if band == "hot":
        return "Priority callback within 24h; share matching listings."
    if band == "warm":
        return "Nurture: send curated options on WhatsApp; follow up in 2-3 days."
    return "Low priority: add to drip campaign."


def _build_key_requirements(lead: LeadProfile) -> str:
    parts = []
    if lead.property_type:
        parts.append(f"{lead.property_type}")
    if lead.preferred_location:
        parts.append(f"in {lead.preferred_location}")
    if lead.city:
        parts.append(f"({lead.city})")
    budget = _format_budget(lead)
    if budget:
        parts.append(f"budget {budget}")
    if lead.buying_timeline:
        parts.append(f"timeline {lead.buying_timeline}")
    if lead.purpose:
        parts.append(lead.purpose)
    if lead.loan_required is not None:
        parts.append("loan needed" if lead.loan_required else "no loan")
    return ", ".join(parts) or "Not captured"


async def _generate_narrative(ctx: CallContext) -> str:
    """LLM-generated 2-line summary (best-effort; falls back to template)."""
    lead = ctx.tracker.lead
    template = (
        f"Caller {lead.name or 'Unknown'} from {lead.city or 'unknown city'} is "
        f"{'interested' if lead.interested else 'not clearly interested'} in a "
        f"{lead.property_type or 'property'}. Requirements: {_build_key_requirements(lead)}."
    )
    if not settings.openai_api_key or not ctx.transcript:
        return template

    transcript_txt = "\n".join(
        f"{t.get('role')}: {t.get('text')}" for t in ctx.transcript[-30:]
    )
    prompt = (
        "Summarize this Hindi/English real-estate qualification call in 2 concise "
        "English sentences focusing on intent and requirements.\n\n" + transcript_txt
    )
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.openai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 120,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # never block completion on summary
        log.warning("completion.narrative.fallback", error=str(exc))
        return template


async def finalize_call(ctx: CallContext, outcome: CallOutcome | None = None) -> dict:
    """Persist final lead state, summary, latency metrics, trigger follow-up.

    Idempotent: safe to call multiple times.
    """
    if ctx.finalized:
        return {}
    ctx.finalized = True

    lead = ctx.tracker.lead
    score = lead.qualification_score()
    band = lead.qualification_band()

    if outcome is None:
        if lead.interested is False:
            outcome = CallOutcome.not_interested
        else:
            outcome = CallOutcome.completed

    narrative = await _generate_narrative(ctx)
    key_reqs = _build_key_requirements(lead)
    next_action = _recommended_next_action(lead)

    lead_status = (
        LeadStatus.qualified
        if band in ("hot", "warm") and lead.interested is not False
        else LeadStatus.unqualified
    )

    async with session_scope() as session:
        lead_repo = LeadRepository(session)
        call_repo = CallRepository(session)
        summary_repo = SummaryRepository(session)

        # Ensure lead persisted with final score/status
        phone = lead.phone_number or ctx.caller_number
        if phone:
            row = await lead_repo.upsert_by_phone(
                phone,
                tenant_id=ctx.tenant_id,
                source=(
                    LeadSource.outbound_call
                    if ctx.direction == "outbound"
                    else LeadSource.inbound_call
                ),
                name=lead.name,
                city=lead.city,
                property_type=lead.property_type,
                budget_min=lead.budget_min,
                budget_max=lead.budget_max,
                preferred_location=lead.preferred_location,
                buying_timeline=lead.buying_timeline,
                purpose=lead.purpose,
                loan_required=lead.loan_required,
                site_visit_interest=lead.site_visit_interest,
                preferred_language=lead.preferred_language,
                qualification_score=score,
                status=lead_status,
            )
            ctx.lead_id = row.id

        # Finalize the call row with latency + outcome
        await call_repo.finalize(
            ctx.call_id,
            ended_at=datetime.now(timezone.utc),
            outcome=outcome,
            final_state=ctx.tracker.state.value,
            **ctx.latency.as_call_fields(),
        )

        await summary_repo.create(
            ctx.call_id,
            summary=narrative,
            key_requirements=key_reqs,
            qualification_score=score,
            recommended_next_action=next_action,
            follow_up_recommendation=(
                "WhatsApp curated listings" if lead.interested is not False else "None"
            ),
            transcript=ctx.transcript[-100:],
        )

        await AuditRepository(session).log(
            "call.finalized",
            entity_type="call",
            entity_id=str(ctx.call_id),
            payload={"outcome": outcome.value, "score": score, "band": band},
        )

        # Campaign reconciliation: fold this finalized call into its target so
        # CampaignTarget becomes the source of truth for campaign analytics.
        if ctx.campaign_id is not None and ctx.lead_id is not None:
            await CampaignRepository(session).reconcile_from_call(
                ctx.campaign_id,
                ctx.lead_id,
                outcome=outcome,
                qualification_score=score,
                interested=lead.interested,
                callback=ctx.callback_booked,
                site_visit_booked=ctx.site_visit_booked,
                call_id=ctx.call_id,
            )

    # Metrics
    m.CALLS_TOTAL.labels(direction=ctx.direction, outcome=outcome.value).inc()
    if lead_status == LeadStatus.qualified:
        m.LEADS_QUALIFIED.inc()

    # Fire-and-record WhatsApp follow-up (Phase 1 = noop logger)
    if lead.interested is not False and (lead.phone_number or ctx.caller_number):
        payload = FollowUpPayload(
            phone_number=lead.phone_number or ctx.caller_number,  # type: ignore[arg-type]
            name=lead.name,
            preferred_language=lead.preferred_language,
            qualification=band,
            property_type=lead.property_type,
            preferred_location=lead.preferred_location,
            budget_summary=_format_budget(lead),
            next_action=next_action,
        )
        try:
            await ctx.whatsapp.trigger(payload)
        except Exception as exc:
            log.warning("completion.whatsapp.error", error=str(exc))

    result = {
        "call_id": str(ctx.call_id),
        "lead": lead.collected_fields(),
        "qualification_score": score,
        "qualification_band": band,
        "key_requirements": key_reqs,
        "summary": narrative,
        "recommended_next_action": next_action,
        "outcome": outcome.value,
    }
    log.info("call.finalized", **{k: result[k] for k in ("call_id", "qualification_score", "outcome")})
    return result
