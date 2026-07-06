"""Priya Agent definition (LiveKit 1.x `Agent`).

All function tools are registered here. The persona lives in `SYSTEM_PROMPT`;
company knowledge is retrieved on demand via the `lookup_knowledge` tool.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from livekit.agents import Agent
from livekit.agents.llm import ToolError, function_tool

from priya.agent.booking_tools import (
    request_agent_transfer,
    schedule_callback,
    schedule_site_visit,
)
from priya.agent.completion_tools import finalize_call_tool
from priya.agent.project_prompt import get_project_system_prompt
from priya.agent.property_tools import lookup_properties
from priya.agent.prompts import get_system_prompt
from priya.agent.transfer import (
    build_hold_audio,
    build_lead_summary,
    make_warm_transfer_task,
    persist_transfer_requested,
    persist_transfer_result,
    whisper_instructions,
)
from priya.agent.tools import (
    advance_state,
    lookup_knowledge,
    mark_not_interested,
    set_language,
    update_lead,
)
from priya.config import settings
from priya.utils.logging import get_logger

log = get_logger(__name__)

# Full set: all 9 tools (richest behaviour).
_FULL_TOOLS = [
    set_language,
    update_lead,
    advance_state,
    lookup_knowledge,
    mark_not_interested,
    schedule_site_visit,
    schedule_callback,
    request_agent_transfer,
    finalize_call_tool,
]

# Lite set: essential tools only (fewer schemas => fewer prompt tokens => lower
# TTFT). Drops set_language, advance_state, mark_not_interested — the persona
# prompt still handles language switching and polite exit conversationally.
_LITE_TOOLS = [
    update_lead,
    lookup_knowledge,
    schedule_site_visit,
    schedule_callback,
    request_agent_transfer,
    finalize_call_tool,
]

# Ultra set: minimal 4 tools (lowest token footprint => lowest TTFT). Drops
# lookup_knowledge (no company Q&A) and request_agent_transfer (callback covers
# the human-agent case). Best for pure qualification + booking at max speed.
_ULTRA_TOOLS = [
    update_lead,
    schedule_site_visit,
    schedule_callback,
    finalize_call_tool,
]

# Project set: single-builder / single-project. No lookup_knowledge because all
# facts are injected into the prompt from the YAML file (zero runtime
# retrieval). schedule_callback doubles as the escalation path for missing info
# or human-agent requests.
_PROJECT_TOOLS = [
    update_lead,
    schedule_site_visit,
    schedule_callback,
    finalize_call_tool,
]

# DB (SaaS multi-tenant) set: like project mode, but adds lookup_properties so
# the LLM queries the tenant's live catalog from Postgres at call time instead
# of relying on a static prompt. Enables dashboard-managed properties.
_DB_TOOLS = [
    update_lead,
    lookup_properties,
    schedule_site_visit,
    schedule_callback,
    finalize_call_tool,
]

_TOOLSETS = {
    "full": _FULL_TOOLS,
    "lite": _LITE_TOOLS,
    "ultra": _ULTRA_TOOLS,
    "project": _PROJECT_TOOLS,
}


_IST = timezone(timedelta(hours=5, minutes=30))


def _datetime_context() -> str:
    """Current IST date/time so the LLM resolves relative times correctly.

    Without this the model hallucinates booking dates (past/wrong year) when a
    caller says 'kal', 'aaj shaam', 'agle hafte'.
    """
    now = datetime.now(_IST)
    return (
        "\n\n# AAJ KA SAMAY (IST)\n"
        f"Abhi: {now.strftime('%A, %d %B %Y, %I:%M %p')} (Asia/Kolkata).\n"
        "Booking ke liye relative time isi ke hisaab se ISO 8601 datetime mein convert karo "
        "(kal = +1 din, parso = +2 din, agle hafte = +7 din).\n"
        "Time-of-day: subah ~10:00, dopahar ~14:00, shaam ~18:00, raat ~20:00. "
        "Date kabhi past mein mat do."
    )


class PriyaAgent(Agent):
    def __init__(
        self,
        instructions: str | None = None,
        tools: list | None = None,
    ) -> None:
        """Build the agent.

        If `instructions` is provided (SaaS/DB mode), the caller has already
        rendered the tenant-specific prompt from the database and passes the
        matching tool set. Otherwise the legacy env-driven modes are used.
        """
        if instructions is not None:
            resolved_instructions = instructions + _datetime_context()
            resolved_tools = tools if tools is not None else _DB_TOOLS
            mode = "db"
        else:
            mode = settings.agent_context_mode.lower()
            if mode == "project":
                resolved_instructions = get_project_system_prompt() + _datetime_context()
                resolved_tools = _PROJECT_TOOLS
            else:
                resolved_instructions = get_system_prompt(mode) + _datetime_context()
                resolved_tools = _TOOLSETS.get(mode, _LITE_TOOLS)
        # Diagnostic: confirm which tools are actually registered at runtime.
        tool_names = [
            getattr(t, "name", getattr(t, "__name__", "?")) for t in resolved_tools
        ]
        log.info("agent.tools_registered", mode=mode, count=len(resolved_tools), names=tool_names)
        super().__init__(instructions=resolved_instructions, tools=resolved_tools)

    # ----------------------------------------------------------------------- #
    # Live human WARM transfer (native LiveKit WarmTransferTask).
    # Registered automatically alongside the tools=[...] list. Only usable when
    # HUMAN_AGENT_PHONE + an outbound SIP trunk are configured.
    # ----------------------------------------------------------------------- #
    @function_tool
    async def transfer_to_human(
        self,
        reason: str = "customer requested a human",
    ) -> str | None:
        """Caller ko live human sales consultant se WARM transfer karo.

        Ye tool tab call karo jab caller human/manager/sales person/consultant/
        representative/senior/live agent se baat karna chahe, ya jab price
        negotiation, discount approval, legal clarification, ya escalation ki
        zaroorat ho, ya high-intent lead turant baat karna chahe.

        Transfer se pehle caller se confirm kar lo. `reason` mein transfer ki
        wajah do (jaise 'price discussion', 'customer asked for manager').
        """
        ctx = self.session.userdata  # CallContext

        # ---- Validate before dialing (security + config guard) ----
        if not (settings.human_agent_phone and settings.sip_outbound_trunk_id):
            log.info("[TRANSFER] unavailable (not configured)")
            return (
                "Transfer abhi available nahi hai. Politely bolo ki sales team se "
                "callback arrange kar sakti ho, aur baat jaari rakho."
            )

        summary = build_lead_summary(ctx, reason)
        log.info("[TRANSFER] Requested", call_id=str(ctx.call_id), reason=reason)
        try:
            await persist_transfer_requested(ctx, summary)
            log.info("[TRANSFER] Summary Generated", call_id=str(ctx.call_id))
        except Exception as exc:  # noqa: BLE001 — persistence must never block a call
            log.error("[TRANSFER] persist_requested_error", error=str(exc))

        # Announce to the caller (they stay on the line; hold music follows).
        await self.session.say(
            "Bilkul sir, main aapko hamare sales consultant se connect karti hoon. "
            "Kripya line par bani rahiye.",
            allow_interruptions=False,
        )

        log.info("[TRANSFER] Human Dialing", to=settings.human_agent_phone)
        try:
            result = await make_warm_transfer_task(
                sip_call_to=settings.human_agent_phone,
                sip_trunk_id=settings.sip_outbound_trunk_id,
                sip_number=settings.vobiz_phone_number or None,
                chat_ctx=self.chat_ctx,
                ringing_timeout=float(settings.transfer_timeout_seconds),
                hold_audio=build_hold_audio(),
                extra_instructions=whisper_instructions(summary),
            )
        except ToolError as exc:
            log.info("[TRANSFER] Transfer Failed", call_id=str(ctx.call_id), error=str(exc))
            await _safe_persist_failed(ctx, summary)
            log.info("[TRANSFER] Cleanup Completed", call_id=str(ctx.call_id))
            # Return to Priya — do NOT disconnect. Speak the apology naturally.
            return (
                "Transfer nahi ho paaya (consultant uplabdh nahi). Caller se kaho: "
                "'Maaf kijiye, is samay hamara consultant uplabdh nahi hai. Main "
                "callback arrange kar sakti hoon.' Phir normal baat jaari rakho."
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("[TRANSFER] Transfer Failed (unexpected)")
            await _safe_persist_failed(ctx, summary)
            log.info("[TRANSFER] Cleanup Completed", call_id=str(ctx.call_id))
            return (
                "Transfer nahi ho paaya. Caller se politely maafi maango aur callback "
                "offer karke normal baat jaari rakho."
            )

        # ---- Success: human answered, whisper delivered, caller bridged ----
        human_id = getattr(result, "human_agent_identity", None)
        log.info("[TRANSFER] Human Answered", human=human_id)
        log.info("[TRANSFER] Call Bridged", call_id=str(ctx.call_id), human=human_id)
        try:
            await persist_transfer_result(
                ctx, summary, outcome="completed", human_identity=human_id
            )
        except Exception as exc:  # noqa: BLE001
            log.error("[TRANSFER] persist_completed_error", error=str(exc))

        ctx.finalized = True  # shutdown hook won't double-finalize
        await self.session.say(
            "Aap hamare consultant se jud gaye hain. Main ab call se hat rahi hoon, "
            "dhanyavaad!",
            allow_interruptions=False,
        )
        log.info("[TRANSFER] Cleanup Completed", call_id=str(ctx.call_id))
        self.session.shutdown()  # Priya exits; caller + human stay bridged.
        return None


async def _safe_persist_failed(ctx, summary) -> None:  # noqa: ANN001
    try:
        await persist_transfer_result(ctx, summary, outcome="failed")
    except Exception as exc:  # noqa: BLE001
        log.error("[TRANSFER] persist_failed_error", error=str(exc))
