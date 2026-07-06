"""Completion function tool exposed to the LLM."""
from __future__ import annotations

from typing import Annotated

from livekit.agents import RunContext, function_tool
from pydantic import Field

from priya.agent.completion import finalize_call
from priya.agent.context import CallContext
from priya.agent.state import ConversationState
from priya.db.models import CallOutcome
from priya.utils.logging import get_logger

log = get_logger(__name__)


@function_tool()
async def finalize_call_tool(
    context: RunContext[CallContext],
    outcome: Annotated[
        str | None,
        Field(
            description="One of: completed, not_interested, callback_requested, "
            "transfer_requested"
        ),
    ] = None,
) -> str:
    """Call ke end par ye tool call karo — jab saari zaroori baat ho gayi ho ya
    caller alvida keh raha ho. Ye lead summary, qualification score aur follow-up
    generate karta hai."""
    ctx = context.userdata
    ctx.tracker.advance_to(ConversationState.CALL_COMPLETION)

    outcome_enum: CallOutcome | None = None
    if outcome:
        try:
            outcome_enum = CallOutcome(outcome)
        except ValueError:
            outcome_enum = None

    result = await finalize_call(ctx, outcome_enum)
    log.info("tool.finalize_call", call_id=str(ctx.call_id))
    return (
        f"Call finalized. Qualification: {result.get('qualification_band')} "
        f"({result.get('qualification_score')}/100). Warmly thank the caller and say goodbye."
    )
