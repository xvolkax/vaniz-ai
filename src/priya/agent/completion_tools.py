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

# Spoken once, right before the line is dropped. Kept here (not in the prompt
# files) intentionally — same as transfer_to_human's hardcoded closing line —
# so call teardown never depends on the LLM choosing to speak a goodbye.
_GOODBYE_LINE = "Aapse baat karke accha laga. Dhanyavaad, aur aapka din shubh rahe!"


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
) -> str | None:
    """Call ke end par ye tool call karo — jab saari zaroori baat ho gayi ho ya
    caller alvida keh raha ho. Ye lead summary, qualification score aur follow-up
    generate karta hai, phir alvida bol kar call disconnect kar deta hai."""
    ctx = context.userdata
    session = context.session

    # ---- Re-entrancy guard (set synchronously, before any await) ----
    # If the LLM emits finalize_call twice (parallel tool calls or a retry), the
    # first invocation owns teardown; later ones become no-ops so we never speak
    # two goodbyes or call session.shutdown() twice. finalize_call() itself is
    # also idempotent (ctx.finalized), so lead/summary/metrics stay single-write.
    if ctx.shutdown_initiated:
        log.info("tool.finalize_call.already_initiated", call_id=str(ctx.call_id))
        return None
    ctx.shutdown_initiated = True

    ctx.tracker.advance_to(ConversationState.CALL_COMPLETION)

    outcome_enum: CallOutcome | None = None
    if outcome:
        try:
            outcome_enum = CallOutcome(outcome)
        except ValueError:
            outcome_enum = None

    # ---- 1) Finalize: save lead, summary, metrics, trigger WhatsApp follow-up ----
    log.info("tool.finalize_call.started", call_id=str(ctx.call_id))
    result = await finalize_call(ctx, outcome_enum)
    log.info(
        "tool.finalize_call.finalized",
        call_id=str(ctx.call_id),
        band=result.get("qualification_band"),
        score=result.get("qualification_score"),
    )

    # ---- 2) Speak the goodbye and WAIT until it has fully played out ----
    # Awaiting the SpeechHandle waits for complete playout (SpeechHandle.__await__
    # -> wait_for_playout), so the caller hears the entire line before we hang up.
    # allow_interruptions=False mirrors transfer_to_human's closing line.
    try:
        await session.say(_GOODBYE_LINE, allow_interruptions=False)
        log.info("tool.finalize_call.goodbye_spoken", call_id=str(ctx.call_id))
    except Exception as exc:  # noqa: BLE001 — never let TTS failure block teardown
        log.warning("tool.finalize_call.goodbye_error", call_id=str(ctx.call_id), error=str(exc))

    # ---- 3) Terminate the call (same mechanism as transfer_to_human) ----
    log.info("tool.finalize_call.shutdown_initiated", call_id=str(ctx.call_id))
    session.shutdown()
    log.info("tool.finalize_call.shutdown_complete", call_id=str(ctx.call_id))

    # Return nothing so the LLM does not generate a further turn after goodbye.
    return None
