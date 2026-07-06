"""LiveKit function tools for Priya.

These are the ONLY way the LLM mutates state / triggers side effects. Each tool
is small, async and non-blocking on the audio path (DB writes are quick and
happen between turns). Tools also drive the conversation state machine.

Uses the LiveKit 1.x `@function_tool` + `RunContext` API (non-deprecated).
"""
from __future__ import annotations

from typing import Annotated, Literal

from livekit.agents import RunContext, function_tool
from pydantic import Field

from priya.agent.context import CallContext
from priya.agent.state import ConversationState
from priya.analytics import metrics as m
from priya.db.database import session_scope
from priya.db.models import LeadSource, LeadStatus
from priya.db.repositories import AuditRepository, LeadRepository
from priya.utils.logging import get_logger

log = get_logger(__name__)


async def _persist_lead(ctx: CallContext) -> None:
    """Upsert the in-call lead profile to PostgreSQL (idempotent by phone)."""
    lead = ctx.tracker.lead
    phone = lead.phone_number or ctx.caller_number
    if not phone:
        return
    async with session_scope() as session:
        repo = LeadRepository(session)
        row = await repo.upsert_by_phone(
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
            qualification_score=lead.qualification_score(),
        )
        ctx.lead_id = row.id


# --------------------------------------------------------------------------- #
# Tool implementations (registered on the Agent via `tools=[...]`)
# --------------------------------------------------------------------------- #
@function_tool()
async def set_language(
    context: RunContext[CallContext],
    language: Annotated[Literal["hi", "en"], Field(description="hi for Hindi, en for English")],
) -> str:
    """Caller ki preferred bhasha set karo. Use when the caller asks to speak in
    English or clearly prefers one language."""
    ctx = context.userdata
    ctx.tracker.lead.preferred_language = language
    m.TOOL_CALLS.labels(tool="set_language").inc()
    log.info("tool.set_language", call_id=str(ctx.call_id), language=language)
    if language == "en":
        return "Language set to English. Continue the conversation in English."
    return "Bhasha Hindi set kar di. Hindi mein baat jaari rakho."


@function_tool()
async def update_lead(
    context: RunContext[CallContext],
    name: Annotated[str | None, Field(description="Caller's full name")] = None,
    city: Annotated[str | None, Field(description="City for property search")] = None,
    property_type: Annotated[
        Literal["apartment", "villa", "plot", "commercial", "other"] | None,
        Field(description="Type of property"),
    ] = None,
    budget_min: Annotated[float | None, Field(description="Min budget in INR (absolute)")] = None,
    budget_max: Annotated[float | None, Field(description="Max budget in INR (absolute)")] = None,
    preferred_location: Annotated[str | None, Field(description="Preferred area/locality")] = None,
    buying_timeline: Annotated[
        str | None, Field(description="e.g. immediate, 3 months, 6 months, 1 year")
    ] = None,
    purpose: Annotated[
        Literal["self_use", "investment"] | None, Field(description="Reason for buying")
    ] = None,
    loan_required: Annotated[bool | None, Field(description="Does caller need a home loan")] = None,
    site_visit_interest: Annotated[
        bool | None, Field(description="Is caller interested in a site visit")
    ] = None,
    interested: Annotated[
        bool | None, Field(description="Is the caller interested in buying at all")
    ] = None,
) -> str:
    """Collected lead detail(s) save karo. Sirf wahi fields bhejo jo abhi mile hain.
    Har nayi jaankari milte hi ye tool call karo (budget lakh/crore ko absolute
    INR mein convert karke bhejo, e.g. 50 lakh = 5000000)."""
    ctx = context.userdata
    lead = ctx.tracker.lead
    updates = {
        "name": name,
        "city": city,
        "property_type": property_type,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "preferred_location": preferred_location,
        "buying_timeline": buying_timeline,
        "purpose": purpose,
        "loan_required": loan_required,
        "site_visit_interest": site_visit_interest,
        "interested": interested,
    }
    applied = {k: v for k, v in updates.items() if v is not None}
    for key, value in applied.items():
        setattr(lead, key, value)

    # NOTE: no DB write here — persisting on every turn adds a round-trip to the
    # hot conversational path. The in-memory profile is flushed to Postgres by
    # finalize_call() (guaranteed via the worker shutdown callback) and by the
    # booking tools when an appointment is created.
    m.TOOL_CALLS.labels(tool="update_lead").inc()
    log.info("tool.update_lead", call_id=str(ctx.call_id), fields=list(applied.keys()))
    return f"Saved: {', '.join(applied.keys())}." if applied else "No new fields."


@function_tool()
async def advance_state(
    context: RunContext[CallContext],
    state: Annotated[
        Literal[
            "greeting",
            "qualification",
            "property_requirements",
            "budget_collection",
            "timeline_collection",
            "appointment_booking",
            "summary",
            "call_completion",
        ],
        Field(description="The conversation stage to move into"),
    ],
) -> str:
    """Conversation ko agle stage mein le jao jab current stage ki jaankari mil jaye."""
    ctx = context.userdata
    ctx.tracker.advance_to(ConversationState(state))
    log.info("tool.advance_state", call_id=str(ctx.call_id), state=state)
    return f"State is now {state}."


@function_tool()
async def lookup_knowledge(
    context: RunContext[CallContext],
    query: Annotated[str, Field(description="What the caller asked about the company/property")],
) -> str:
    """Company/property se related sawaal ke liye knowledge base search karo.
    Prices, RERA, brokerage, locations, home-loan jaise sawaalon par ye use karo."""
    ctx = context.userdata
    m.TOOL_CALLS.labels(tool="lookup_knowledge").inc()
    chunks = await ctx.knowledge.search(query, top_k=2)
    if not chunks:
        return "Is baare mein specific jaankari abhi available nahi hai."
    return "\n\n".join(c.content for c in chunks)


@function_tool()
async def mark_not_interested(context: RunContext[CallContext]) -> str:
    """Agar caller clearly interested nahi hai to ye call karo. Politely close karna hai."""
    ctx = context.userdata
    ctx.tracker.lead.interested = False
    ctx.tracker.advance_to(ConversationState.CALL_COMPLETION)
    async with session_scope() as session:
        if ctx.lead_id:
            await LeadRepository(session).set_status(ctx.lead_id, LeadStatus.unqualified)
        await AuditRepository(session).log(
            "lead.not_interested", entity_type="lead", entity_id=str(ctx.lead_id)
        )
    log.info("tool.mark_not_interested", call_id=str(ctx.call_id))
    return "Marked not interested. Politely thank the caller and end the call."
