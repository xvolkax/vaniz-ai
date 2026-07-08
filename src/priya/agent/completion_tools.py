"""Completion function tool exposed to the LLM."""
from __future__ import annotations

import asyncio
from typing import Annotated

from livekit.agents import RunContext, function_tool
from pydantic import Field

from priya.agent.completion import finalize_call
from priya.agent.context import CallContext
from priya.agent.state import ConversationState
from priya.db.models import CallOutcome
from priya.telephony.control import end_call
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
    outcome_enum: CallOutcome | None = None
    if outcome:
        try:
            outcome_enum = CallOutcome(outcome)
        except ValueError:
            outcome_enum = None
    await end_call_and_hangup(context.session, context.userdata, outcome_enum)
    return None


async def end_call_and_hangup(
    session,  # noqa: ANN001 — AgentSession (avoids importing heavy type)
    ctx: CallContext,
    outcome_enum: CallOutcome | None = None,
) -> bool:
    """Finalize + speak goodbye + actually drop the caller. Idempotent.

    Callable from BOTH the finalize_call tool (LLM-driven) and the worker's
    deterministic hangup-intent detector, so the call ends on the first explicit
    disconnect request even if the LLM forgets to call the tool.

    Returns True if this invocation performed the teardown, False if another
    path already started it.
    """
    # Re-entrancy guard set synchronously (before any await) so the tool path and
    # the intent-detector path can never both run teardown / speak two goodbyes.
    if ctx.shutdown_initiated:
        log.info("tool.finalize_call.already_initiated", call_id=str(ctx.call_id))
        return False
    ctx.shutdown_initiated = True

    ctx.tracker.advance_to(ConversationState.CALL_COMPLETION)

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
    try:
        await session.say(_GOODBYE_LINE, allow_interruptions=False)
        log.info("tool.finalize_call.goodbye_spoken", call_id=str(ctx.call_id))
    except Exception as exc:  # noqa: BLE001 — never let TTS failure block teardown
        log.warning("tool.finalize_call.goodbye_error", call_id=str(ctx.call_id), error=str(exc))

    # Small guard so the tail of the goodbye reaches the caller's SIP leg before
    # the room is torn down (playout completion != carrier-side flush).
    await asyncio.sleep(0.5)

    # ---- 3) Terminate the call — DROP THE CALLER, not just the agent ----
    log.info("tool.finalize_call.shutdown_initiated", call_id=str(ctx.call_id))
    try:
        await end_call(ctx.room_name)
    except Exception as exc:  # noqa: BLE001
        log.error("tool.finalize_call.end_call_error", call_id=str(ctx.call_id), error=str(exc))
        try:
            session.shutdown()
        except Exception:  # noqa: BLE001
            pass
    log.info("tool.finalize_call.shutdown_complete", call_id=str(ctx.call_id))
    return True
