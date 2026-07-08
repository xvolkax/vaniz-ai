"""LiveKit Agent worker entrypoint (non-deprecated 1.x architecture).

Pipeline (all streaming, non-blocking):
    Deepgram Nova-3 (multi)  ->  GPT-4o-mini  ->  Cartesia Sonic
    + Silero VAD + LiveKit MultilingualModel turn detector (semantic endpointing)
    + BVCTelephony noise cancellation tuned for phone audio.

Handles inbound & outbound SIP calls dispatched to `AGENT_NAME`.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone

from livekit.agents import (
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
)
from livekit.agents import inference
from livekit.plugins import cartesia, silero

from priya.agent.assistant import PriyaAgent
from priya.agent.completion import finalize_call
from priya.agent.completion_tools import end_call_and_hangup
from priya.agent.context import CallContext
from priya.agent.llm_factory import build_llm
from priya.agent.project_prompt import build_greeting, build_system_prompt, get_project_greeting
from priya.agent.prompts import GREETING_HINDI
from priya.agent.state import ConversationTracker
from priya.agent.stt_factory import build_stt
from priya.agent.tenant_knowledge import (
    load_active_properties,
    render_tenant_knowledge,
    resolve_tenant,
)
from priya.analytics import metrics as m
from priya.analytics.latency import LatencyTracker
from priya.analytics.turn_latency import TurnLatencyLogger
from priya.calendar.factory import get_calendar_provider
from priya.config import settings
from priya.crm.factory import get_crm_adapter
from priya.db.database import session_scope
from priya.db.models import CallDirection
from priya.db.repositories import CallRepository
from priya.knowledge.factory import get_retriever
from priya.utils.logging import configure_logging, get_logger
from priya.whatsapp.factory import get_follow_up_service

log = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Deterministic end-call intent detection.
# gpt-4o-mini sometimes speaks a goodbye without calling finalize_call, leaving
# the caller connected. This net catches explicit disconnect requests and tears
# the call down on the FIRST request, regardless of whether the LLM cooperates.
# Kept intentionally narrow (needs a call/phone object + an end action, or an
# unambiguous verb) so mid-call phrases like "thank you" don't hang up.
# --------------------------------------------------------------------------- #
_HANGUP_STRONG = (
    "disconnect", "hang up", "hangup", "kaat do", "kaat dijiye", "kaat dena",
    "kaat do call", "line kaat", "phone kaat", "call kaat",
)
_HANGUP_OBJECTS = ("call", "phone", "line", "kaal")
_HANGUP_ACTIONS = ("band", "rakh", "khatam", "cut", "kaat", "end", "disconnect", "kaat")


def _is_hangup_request(text: str) -> bool:
    """True when the caller clearly asks to end/disconnect the call."""
    t = (text or "").lower().strip()
    if not t:
        return False
    if any(p in t for p in _HANGUP_STRONG):
        return True
    if any(o in t for o in _HANGUP_OBJECTS) and any(a in t for a in _HANGUP_ACTIONS):
        return True
    return False


# --------------------------------------------------------------------------- #
# Prewarm — load the VAD once per process (expensive), reused across jobs.
# --------------------------------------------------------------------------- #
def prewarm(proc: JobProcess) -> None:
    configure_logging()
    proc.userdata["vad"] = silero.VAD.load(
        min_silence_duration=0.25,  # snappy endpointing, tuned with turn detector
    )
    # Surface recording misconfiguration once per worker process at startup.
    try:
        from priya.telephony.recording import log_recording_config_status

        log_recording_config_status("agent")
    except Exception as exc:  # noqa: BLE001 — never block prewarm
        log.debug("worker.recording.config_check_error", error=str(exc))
    log.info("worker.prewarm.complete")


def _extract_call_info(ctx: JobContext) -> tuple[CallDirection, str | None, str | None, str | None]:
    """Determine direction, caller number, tenant_id, and campaign_id from metadata."""
    direction = CallDirection.inbound
    caller: str | None = None
    tenant_id: str | None = None
    campaign_id: str | None = None

    # Outbound calls carry JSON metadata we set at dispatch time.
    if ctx.job and ctx.job.metadata:
        try:
            meta = json.loads(ctx.job.metadata)
            if meta.get("direction") == "outbound":
                direction = CallDirection.outbound
            caller = meta.get("phone_number") or caller
            tenant_id = meta.get("tenant_id") or tenant_id
            campaign_id = meta.get("campaign_id") or campaign_id
        except (json.JSONDecodeError, TypeError):
            pass
    return direction, caller, tenant_id, campaign_id


def _dialed_number(ctx: JobContext) -> str | None:
    """The number the caller dialed (tenant DID) — used for tenant routing."""
    for participant in ctx.room.remote_participants.values():
        attrs = participant.attributes or {}
        num = attrs.get("sip.trunkPhoneNumber") or attrs.get("sip.to")
        if num:
            return num
    return None


def _caller_from_participant(ctx: JobContext) -> str | None:
    """Read SIP caller number from remote participant attributes if present."""
    for participant in ctx.room.remote_participants.values():
        attrs = participant.attributes or {}
        num = attrs.get("sip.phoneNumber") or attrs.get("sip.from")
        if num:
            return num
    return None


async def entrypoint(ctx: JobContext) -> None:
    configure_logging()
    await ctx.connect()
    log.info("worker.job.start", room=ctx.room.name)

    direction, caller, meta_tenant_id, meta_campaign_id = _extract_call_info(ctx)

    # Wait briefly for the SIP participant so we can capture the caller number.
    try:
        participant = await ctx.wait_for_participant()
        caller = caller or (participant.attributes or {}).get("sip.phoneNumber")
    except Exception:  # noqa: BLE001
        pass
    caller = caller or _caller_from_participant(ctx)

    # ---- Resolve tenant (multi-tenant routing) ----
    # Outbound: tenant_id comes from dispatch metadata. Inbound: resolve by the
    # dialed DID; fall back to DEFAULT_TENANT_SLUG for single-tenant/dev.
    tenant = None
    tenant_id: uuid.UUID | None = None
    if settings.knowledge_source.lower() == "db":
        try:
            parsed_meta_tenant = uuid.UUID(meta_tenant_id) if meta_tenant_id else None
        except (ValueError, TypeError):
            parsed_meta_tenant = None
        tenant = await resolve_tenant(
            tenant_id=parsed_meta_tenant,
            dialed_number=_dialed_number(ctx),
            default_slug=settings.default_tenant_slug or None,
        )
        if tenant is not None:
            tenant_id = tenant.id
            log.info("worker.tenant.resolved", tenant=tenant.slug, tenant_id=str(tenant.id))
        else:
            log.warning("worker.tenant.unresolved", room=ctx.room.name)

    # ---- Persist an initial Call row ----
    call_id = uuid.uuid4()
    try:
        campaign_uuid = uuid.UUID(meta_campaign_id) if meta_campaign_id else None
    except (ValueError, TypeError):
        campaign_uuid = None
    async with session_scope() as session:
        await CallRepository(session).create(
            id=call_id,
            tenant_id=tenant_id,
            campaign_id=campaign_uuid,
            room_name=ctx.room.name,
            direction=direction,
            from_number=caller if direction == CallDirection.inbound else settings.vobiz_phone_number,
            to_number=settings.vobiz_phone_number if direction == CallDirection.inbound else caller,
        )

    # ---- Build per-call context with pluggable services ----
    tracker = ConversationTracker()
    tracker.lead.phone_number = caller
    latency = LatencyTracker(call_id=str(call_id))
    call_ctx = CallContext(
        call_id=call_id,
        room_name=ctx.room.name,
        direction=direction.value,
        caller_number=caller,
        tracker=tracker,
        latency=latency,
        crm=get_crm_adapter(),
        calendar=get_calendar_provider(),
        whatsapp=get_follow_up_service(),
        knowledge=get_retriever(),
        tenant_id=tenant_id,
        campaign_id=campaign_uuid,
    )

    m.ACTIVE_CALLS.inc()

    # ---- Answer detection (accurate duration + real answer-rate) ----
    # Duration must be billed from the moment the callee actually picks up, not
    # from when the agent job connected. Inbound callers are already on the line
    # when the agent joins, so they count as answered immediately. Outbound calls
    # are only "answered" once the SIP callStatus flips to "active" (or, as a
    # fallback, once the first real user speech is transcribed — see _wire_events).
    def _mark_answered() -> None:
        if not call_ctx.answered:
            call_ctx.answered = True
            call_ctx.answered_at = datetime.now(timezone.utc)
            log.info("worker.call.answered", call_id=str(call_id), direction=direction.value)

    if direction == CallDirection.inbound:
        _mark_answered()
    else:
        # Outbound: watch the SIP participant's callStatus for the pickup moment.
        def _check_sip_status(participant) -> None:  # noqa: ANN001
            try:
                status = (getattr(participant, "attributes", {}) or {}).get("sip.callStatus")
                if status == "active":
                    _mark_answered()
            except Exception:  # noqa: BLE001
                pass

        @ctx.room.on("participant_attributes_changed")
        def _on_attrs_changed(_changed, participant) -> None:  # noqa: ANN001
            _check_sip_status(participant)

        @ctx.room.on("participant_connected")
        def _on_participant_connected(participant) -> None:  # noqa: ANN001
            _check_sip_status(participant)

        # Participant may already be active by the time we wire the handlers.
        for p in ctx.room.remote_participants.values():
            _check_sip_status(p)

    # ---- Cartesia TTS kwargs (only pass a voice when configured) ----
    # sonic-3: sonic-2 was sunsetted by Cartesia. word_timestamps disabled because
    # Cartesia only aligns timestamps for en/de/es/fr on sonic models (Hindi warns),
    # and we don't need aligned transcripts on the telephony path.
    tts_kwargs: dict = {
        "model": settings.cartesia_model,        # sonic-3
        "language": settings.cartesia_language,  # hi
        "word_timestamps": False,
    }
    if settings.cartesia_voice_id:
        tts_kwargs["voice"] = settings.cartesia_voice_id

    # ---- Turn handling (non-deprecated 1.6.4 API) ----
    # TURN_DETECTION_MODE=livekit -> LiveKit-hosted semantic EOU detector
    # (inference.TurnDetector): no local model files (model_q8.onnx/languages.json),
    # runs in India West for low latency. Fallbacks: "vad" (pure VAD, fully local)
    # or "stt". Endpointing kept tight; max_delay capped so an uncertain turn
    # never stalls the caller.
    mode = settings.turn_detection_mode.lower()
    if mode == "livekit":
        turn_detection: object = inference.TurnDetector()
    else:
        turn_detection = mode  # "vad" | "stt" | "manual"

    turn_handling: dict = {
        "turn_detection": turn_detection,
        "endpointing": {
            "mode": "fixed",
            "min_delay": settings.min_endpointing_delay,
            "max_delay": settings.max_endpointing_delay,
        },
        "interruption": {"enabled": settings.allow_interruptions},
        "preemptive_generation": {"enabled": True, "preemptive_tts": True},
    }

    # ---- LLM (provider selected via LLM_PROVIDER: openai | azure | groq) ----
    llm = build_llm()

    # ---- STT (provider selected via STT_PROVIDER: deepgram | sarvam) ----
    stt = build_stt()

    # ---- Assemble the streaming session (lowest-latency config) ----
    session: AgentSession[CallContext] = AgentSession(
        userdata=call_ctx,
        stt=stt,
        llm=llm,
        tts=cartesia.TTS(**tts_kwargs),
        vad=ctx.proc.userdata["vad"],
        turn_handling=turn_handling,
    )

    _wire_events(session, call_ctx)

    # ---- Build the agent: DB-driven (multi-tenant) prompt when available ----
    agent_instructions: str | None = None
    greeting: str
    if tenant is not None:
        props = await load_active_properties(tenant.id)
        knowledge = render_tenant_knowledge(tenant, props)
        agent_instructions = build_system_prompt(
            builder=tenant.builder_name or tenant.name,
            region=tenant.region or "",
            knowledge=knowledge,
        )
        greeting = build_greeting(tenant.builder_name or tenant.name, tenant.region)
        log.info("worker.knowledge.db", tenant=tenant.slug, properties=len(props))
    else:
        greeting = (
            get_project_greeting()
            if settings.agent_context_mode.lower() == "project"
            else GREETING_HINDI
        )

    # ---- Shutdown hook: guarantee finalization even on abrupt hangup ----
    # Pass no explicit outcome so finalize_call classifies correctly: never
    # answered -> no_answer (0s), otherwise completed / not_interested.
    async def _on_shutdown() -> None:
        m.ACTIVE_CALLS.dec()
        try:
            await finalize_call(call_ctx)
        except Exception as exc:  # noqa: BLE001
            log.error("worker.finalize.error", error=str(exc))

    ctx.add_shutdown_callback(_on_shutdown)

    # ---- Start & greet immediately (perceived latency ~ TTS first byte) ----
    # BVCTelephony noise cancellation is tuned for 8kHz phone audio but requires a
    # LiveKit Cloud entitlement; when unavailable the FFI audio filter fails with
    # "not authenticated". It is therefore opt-in via NOISE_CANCELLATION_ENABLED.
    # delete_room_on_close=False keeps the room alive after Priya shuts down so a
    # warm transfer (caller + human) stays connected once Priya exits.
    room_input_options = RoomInputOptions(delete_room_on_close=False)
    if settings.noise_cancellation_enabled:
        try:
            from livekit.plugins import noise_cancellation

            room_input_options = RoomInputOptions(
                noise_cancellation=noise_cancellation.BVCTelephony(),
                delete_room_on_close=False,
            )
        except Exception as exc:  # noqa: BLE001
            log.info("worker.noise_cancellation.disabled", reason=str(exc))

    # ---- Start recording BEFORE the greeting so the ENTIRE call is captured ----
    # Egress was previously started AFTER `generate_reply(greeting)`, so it only
    # began once Priya's opening line had fully played — clipping the first
    # several seconds (e.g. 37s call -> 28s recording). Starting it here, before
    # session.start(), records the full conversation from call pickup. Stores
    # ONLY the object key (bucket stays private; playback via presigned URLs).
    if settings.recording_enabled:
        try:
            from priya.telephony.recording import start_room_recording

            rec_key = await start_room_recording(ctx.room.name, str(call_id))
            if rec_key:
                # Distinct var name — must NOT shadow the AgentSession `session`.
                async with session_scope() as db:
                    await CallRepository(db).set_recording_key(call_id, rec_key)
        except Exception as exc:  # noqa: BLE001
            log.warning("worker.recording.error", error=str(exc))

    await session.start(
        agent=PriyaAgent(instructions=agent_instructions),
        room=ctx.room,
        room_input_options=room_input_options,
    )

    await session.generate_reply(instructions=f"Say exactly: {greeting}")


def _wire_events(session: AgentSession, call_ctx: CallContext) -> None:
    """Attach latency, transcript and interruption event handlers.

    Two latency consumers, both fed from the official 1.6 events:
      * LatencyTracker    -> Prometheus histograms + per-call DB averages
      * TurnLatencyLogger -> compact greppable per-turn [LATENCY]/[TURN]/[TOOL] logs
    """
    turns = TurnLatencyLogger(call_id=str(call_ctx.call_id))

    @session.on("metrics_collected")
    def _on_metrics(ev) -> None:  # noqa: ANN001
        try:
            call_ctx.latency.on_livekit_metrics(ev.metrics)
            turns.on_metrics(ev.metrics)
        except Exception as exc:  # noqa: BLE001
            log.debug("worker.metrics.handler_error", error=str(exc))

    @session.on("conversation_item_added")
    def _on_item(ev) -> None:  # noqa: ANN001
        try:
            item = ev.item
            role = getattr(item, "role", "unknown")
            text = getattr(item, "text_content", None) or ""
            if text:
                call_ctx.transcript.append({"role": role, "text": text})
        except Exception as exc:  # noqa: BLE001
            log.debug("worker.transcript.handler_error", error=str(exc))

    # ---- Per-turn latency: tool lifecycle + counts ----
    @session.on("tool_execution_updated")
    def _on_tool_update(ev) -> None:  # noqa: ANN001
        turns.on_tool_update(ev)

    @session.on("function_tools_executed")
    def _on_tools_executed(ev) -> None:  # noqa: ANN001
        turns.on_tools_executed(ev)

    # ---- Per-turn latency: STT final transcript timeline ----
    @session.on("user_input_transcribed")
    def _on_transcribed(ev) -> None:  # noqa: ANN001
        try:
            if getattr(ev, "is_final", False):
                transcript = getattr(ev, "transcript", "") or ""
                # Fallback answer signal: real user speech means the line is live,
                # even if the SIP callStatus event was missed.
                if not call_ctx.answered:
                    call_ctx.answered = True
                    call_ctx.answered_at = datetime.now(timezone.utc)
                    log.info("worker.call.answered", call_id=str(call_ctx.call_id), via="stt")
                # Deterministic hangup: if the caller clearly asks to end the call,
                # tear it down on the first request without relying on the LLM to
                # call finalize_call. Idempotent guard prevents double teardown.
                if _is_hangup_request(transcript) and not call_ctx.shutdown_initiated:
                    log.info(
                        "worker.hangup_intent.detected",
                        call_id=str(call_ctx.call_id),
                        text=transcript[:80],
                    )
                    asyncio.create_task(end_call_and_hangup(session, call_ctx))
                turns.on_stt_final(transcript)
        except Exception as exc:  # noqa: BLE001
            log.debug("worker.transcribed.handler_error", error=str(exc))

    # Interruption / barge-in tracking via state changes.
    state = {"agent_speaking": False}

    @session.on("agent_state_changed")
    def _on_agent_state(ev) -> None:  # noqa: ANN001
        old = getattr(ev, "old_state", "")
        new = getattr(ev, "new_state", "")
        state["agent_speaking"] = new == "speaking"
        turns.on_agent_state(old, new)

    @session.on("user_state_changed")
    def _on_user_state(ev) -> None:  # noqa: ANN001
        old = getattr(ev, "old_state", "")
        new = getattr(ev, "new_state", "")
        if new == "speaking" and state["agent_speaking"]:
            call_ctx.latency.record_interruption()
        turns.on_user_state(old, new)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name=settings.agent_name,
        )
    )
