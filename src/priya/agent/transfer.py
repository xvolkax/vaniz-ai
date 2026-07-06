"""Warm human transfer — helpers around LiveKit's native ``WarmTransferTask``.

The actual orchestration (hold music, private consultation room, whisper to the
human, move-participant bridge, ringing timeout, voicemail/decline handling) is
done by ``livekit.agents.beta.workflows.WarmTransferTask``. This module only:

  * builds the structured lead summary + the private whisper instructions,
  * builds the caller hold-music audio,
  * persists the transfer lifecycle to Postgres (AuditLog + Appointment + Call)
    WITHOUT a schema migration — reusing existing tables.

Customer never hears the whisper: the human is dialled into a SEPARATE
consultation room by the task; the summary is spoken there, then the human is
moved into the caller's room and Priya exits.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from priya.agent.context import CallContext
from priya.config import settings
from priya.db.database import session_scope
from priya.db.models import (
    AppointmentStatus,
    AppointmentType,
    CallOutcome,
)
from priya.db.repositories import (
    AppointmentRepository,
    AuditRepository,
    CallRepository,
)
from priya.utils.logging import get_logger

log = get_logger(__name__)


def _format_budget(lead: Any) -> str | None:
    """Render the lead budget (absolute INR) as a speakable lakh/crore string."""
    def fmt(v: float) -> str:
        if v >= 1_00_00_000:
            return f"{v / 1_00_00_000:.2f}".rstrip("0").rstrip(".") + " crore"
        return f"{int(round(v / 1_00_000))} lakh"

    lo, hi = lead.budget_min, lead.budget_max
    if lo and hi and lo != hi:
        return f"{fmt(lo)} - {fmt(hi)}"
    if hi:
        return fmt(hi)
    if lo:
        return fmt(lo)
    return None


def make_warm_transfer_task(**kwargs):
    """Return a WarmTransferTask that delivers the whisper IMMEDIATELY on answer.

    The stock ``WarmTransferTask`` waits for the human to speak first (see its
    ``on_enter``: "# let the human speak first"), which on a phone call means the
    consultant picks up to silence, says "hello", and only THEN — after STT +
    endpointing + a cold LLM summary — does the AI talk (~5-7s felt delay).

    We subclass and, as soon as ``super().on_enter()`` returns (the SIP call was
    answered and the human session exists), we trigger the summary reply. This
    removes the human-speaks + STT + endpointing latency and the awkward silence.
    """
    from livekit.agents.beta.workflows import WarmTransferTask

    class _ImmediateWhisperWarmTransferTask(WarmTransferTask):
        async def on_enter(self) -> None:
            await super().on_enter()
            # super().on_enter() blocks until the dial is answered; on success it
            # sets self._human_agent_sess. On failure it completes the task.
            if not self.done() and self._human_agent_sess is not None:
                try:
                    self._human_agent_sess.generate_reply()
                    log.info("[TRANSFER] Whisper Started")
                except Exception as exc:  # noqa: BLE001
                    log.info("transfer.immediate_whisper.skipped", reason=str(exc))

    return _ImmediateWhisperWarmTransferTask(**kwargs)


def build_lead_summary(ctx: CallContext, reason: str) -> dict:
    """Structured lead summary (stored + used for the human whisper)."""
    lead = ctx.tracker.lead
    return {
        "name": lead.name,
        "phone": lead.phone_number or ctx.caller_number,
        "purpose": lead.purpose,
        "budget": _format_budget(lead),
        "location": lead.preferred_location or lead.city,
        "property_type": lead.property_type,
        "loan_required": lead.loan_required,
        "timeline": lead.buying_timeline,
        "project_interest": (lead.extra or {}).get("project_interest")
        if hasattr(lead, "extra")
        else None,
        "conversation_summary": None,  # WarmTransferTask generates the spoken one
        "reason_for_transfer": reason,
    }


def whisper_instructions(summary: dict) -> str:
    """Extra instructions for WarmTransferTask -> the private whisper the human
    hears (customer never hears this). Keeps it short and Hinglish."""
    def line(label: str, value: Any) -> str:
        return f"{label}: {value}" if value not in (None, "") else ""

    facts = "\n".join(
        f
        for f in (
            line("Name", summary.get("name")),
            line("Phone", summary.get("phone")),
            line("Budget", summary.get("budget")),
            line("Property type", summary.get("property_type")),
            line("Location", summary.get("location")),
            line("Timeline", summary.get("timeline")),
            line("Loan required", summary.get("loan_required")),
            line("Reason for transfer", summary.get("reason_for_transfer")),
        )
        if f
    )
    return (
        "You are Priya, the AI assistant who just spoke with this customer. "
        "Give the human sales consultant a SHORT private hand-off in natural "
        "Hinglish (2 short sentences max), first-person. Start with "
        "'Ek naya lead Priya AI se.' Then state the key facts below and the "
        "reason for transfer. Do NOT ask the customer anything — the customer "
        "cannot hear you.\n\n"
        f"Known lead details:\n{facts}"
    )


def build_hold_audio():
    """Native hold music for the caller while the human is dialled. Returns an
    AudioConfig or None (silent hold) — never raises."""
    if not settings.transfer_hold_music:
        return None
    try:
        from livekit.agents import AudioConfig, BuiltinAudioClip

        return AudioConfig(BuiltinAudioClip.HOLD_MUSIC, volume=0.8)
    except Exception as exc:  # noqa: BLE001
        log.info("transfer.hold_audio.unavailable", reason=str(exc))
        return None


# --------------------------------------------------------------------------- #
# Persistence (no schema migration — reuses AuditLog / Appointment / Call)
# --------------------------------------------------------------------------- #
async def persist_transfer_requested(ctx: CallContext, summary: dict) -> None:
    """Record the transfer request: audit event + agent_transfer appointment."""
    from priya.agent.tools import _persist_lead

    if ctx.lead_id is None:
        await _persist_lead(ctx)

    now = datetime.now(timezone.utc)
    async with session_scope() as session:
        if ctx.lead_id:
            await AppointmentRepository(session).create(
                lead_id=ctx.lead_id,
                type=AppointmentType.agent_transfer,
                status=AppointmentStatus.scheduled,
                scheduled_at=now,
                duration_minutes=15,
                notes=f"Warm transfer to {settings.human_agent_phone}. "
                f"Reason: {summary.get('reason_for_transfer')}",
            )
        await AuditRepository(session).log(
            "transfer.requested",
            entity_type="call",
            entity_id=str(ctx.call_id),
            payload={
                "transfer_requested_at": now.isoformat(),
                "human_agent_number": settings.human_agent_phone,
                "caller_number": ctx.caller_number,
                "call_id": str(ctx.call_id),
                "reason": summary.get("reason_for_transfer"),
                "lead_summary": summary,
            },
        )


async def persist_transfer_result(
    ctx: CallContext, summary: dict, *, outcome: str, human_identity: str | None = None
) -> None:
    """Record the transfer outcome (completed | failed) + update the call row."""
    now = datetime.now(timezone.utc)
    async with session_scope() as session:
        await AuditRepository(session).log(
            f"transfer.{outcome}",
            entity_type="call",
            entity_id=str(ctx.call_id),
            payload={
                "transfer_completed_at": now.isoformat(),
                "transfer_outcome": outcome,
                "human_agent_number": settings.human_agent_phone,
                "human_agent_identity": human_identity,
                "caller_number": ctx.caller_number,
                "call_id": str(ctx.call_id),
                "reason": summary.get("reason_for_transfer"),
                "lead_summary": summary,
            },
        )
        if outcome == "completed":
            await CallRepository(session).finalize(
                ctx.call_id, outcome=CallOutcome.transfer_requested
            )
