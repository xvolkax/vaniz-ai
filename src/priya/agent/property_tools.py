"""Dynamic, DB-backed property lookup tool for the agent.

Replaces the static YAML-in-prompt approach: the LLM calls `lookup_properties`
during the call, which queries the CURRENT tenant's live catalog from Postgres.
Dashboard edits are therefore reflected on the very next call.
"""
from __future__ import annotations

from typing import Annotated, Literal

from livekit.agents import RunContext, function_tool
from pydantic import Field

from priya.agent.context import CallContext
from priya.analytics import metrics as m
from priya.db.database import session_scope
from priya.db.models import PropertyType
from priya.db.repositories import PropertyRepository
from priya.utils.logging import get_logger

log = get_logger(__name__)


def _format(prop) -> str:  # noqa: ANN001
    parts = [prop.project_name]
    meta = ", ".join(x for x in (prop.property_type.value, prop.location or "") if x)
    if meta:
        parts.append(f"({meta})")
    for label, val in (
        ("Price", prop.price),
        ("Possession", prop.possession),
        ("Carpet", prop.carpet_area),
        ("RERA", prop.rera),
        ("Amenities", ", ".join(prop.amenities) if prop.amenities else None),
        ("Connectivity", prop.connectivity),
    ):
        if val:
            parts.append(f"{label}: {val}")
    return " | ".join(parts)


@function_tool()
async def lookup_properties(
    context: RunContext[CallContext],
    property_type: Annotated[
        Literal["apartment", "villa", "plot", "commercial", "other"] | None,
        Field(description="Filter by property type if the caller specified one"),
    ] = None,
    location: Annotated[
        str | None, Field(description="Preferred area/locality mentioned by the caller")
    ] = None,
    budget_max: Annotated[
        float | None, Field(description="Caller's max budget in absolute INR, e.g. 8000000")
    ] = None,
) -> str:
    """Caller ke budget/area/type ke hisaab se hamare projects search karo.

    Prices, locations, possession jaise property sawaalon par ye tool use karo.
    Sirf isi list se jawab do — koi project ya price invent mat karo."""
    ctx = context.userdata
    m.TOOL_CALLS.labels(tool="lookup_properties").inc()

    if ctx.tenant_id is None:
        return "Abhi property list available nahi hai. Sales team callback arrange kar degi."

    ptype = PropertyType(property_type) if property_type else None
    async with session_scope() as session:
        rows = await PropertyRepository(session).search(
            ctx.tenant_id,
            property_type=ptype,
            location=location,
            budget_max=budget_max,
            limit=5,
        )

    log.info(
        "tool.lookup_properties",
        call_id=str(ctx.call_id),
        results=len(rows),
        ptype=property_type,
        location=location,
    )
    if not rows:
        return (
            "In criteria par abhi koi matching project nahi mila. Caller se thoda "
            "flexible budget/area poochho, ya sales-team callback offer karo."
        )
    return "Matching projects:\n" + "\n".join(f"- {_format(r)}" for r in rows)
