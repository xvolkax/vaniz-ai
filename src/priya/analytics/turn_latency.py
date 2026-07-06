"""Per-turn end-to-end latency instrumentation (LiveKit Agents 1.6.x).

Uses the official metrics/events API — no plugin-internal hacks:

  * ``metrics_collected``  -> typed EOU/LLM/TTS metrics, grouped by ``speech_id``
  * ``tool_execution_updated`` -> ToolCallStarted / ToolCallEnded (per-tool timing)
  * ``function_tools_executed`` -> tool count for the turn (none/single/multiple)
  * ``user_state_changed`` / ``agent_state_changed`` / ``user_input_transcribed``
    -> speech-start/end + STT-final timeline

Emits compact, greppable lines:

    [LATENCY] TURN=3 STT_FINAL=412ms
    [LATENCY] TURN=3 LLM_TTFT=1087ms LLM_TOTAL=1450ms
    [LATENCY] TURN=3 TTS_FIRST_BYTE=241ms
    [TURN] TURN=3 STT_FINAL_DELAY=412ms LLM_TTFT=1087ms LLM_TOTAL=1450ms \
TTS_FIRST_BYTE=241ms TTS_TOTAL=980ms E2E_USER_END_TO_AGENT_START=1740ms TOOLS=single
    [TOOL] TOOL_START update_lead
    [TOOL] TOOL_END update_lead duration=1.8ms status=done

Timing values are milliseconds. This module only *reads* metrics/events and
logs; it never changes prompts, tools, turn detection or business logic.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from priya.utils.logging import get_logger

log = get_logger("priya.latency")


def _ms(seconds: float | None) -> float | None:
    if seconds is None or seconds < 0:
        return None
    return round(seconds * 1000, 1)


@dataclass
class _TurnRecord:
    turn: int
    stt_final_ms: float | None = None       # EOUMetrics.transcription_delay
    eou_delay_ms: float | None = None        # EOUMetrics.end_of_utterance_delay
    llm_ttft_ms: float | None = None         # LLMMetrics.ttft
    llm_total_ms: float | None = None        # LLMMetrics.duration
    tts_ttfb_ms: float | None = None         # TTSMetrics.ttfb (first segment)
    tts_total_ms: float = 0.0                # sum of TTSMetrics.duration
    tools: int = 0
    summarised: bool = False


@dataclass
class TurnLatencyLogger:
    """Groups per-turn metrics by ``speech_id`` and logs a compact summary."""

    call_id: str
    _records: dict[str, _TurnRecord] = field(default_factory=dict)
    _turn_no: dict[str, int] = field(default_factory=dict)
    _next_turn: int = 0
    # call_id -> (tool_name, monotonic_start)
    _tool_starts: dict[str, tuple[str, float]] = field(default_factory=dict)
    _pending_tool_count: int = 0

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _rec(self, speech_id: str | None) -> _TurnRecord:
        sid = speech_id or "unknown"
        if sid not in self._turn_no:
            self._next_turn += 1
            self._turn_no[sid] = self._next_turn
            self._records[sid] = _TurnRecord(turn=self._next_turn)
        return self._records[sid]

    # ------------------------------------------------------------------ #
    # metrics (from `metrics_collected`)
    # ------------------------------------------------------------------ #
    def on_metrics(self, mtr: object) -> None:
        try:
            cls = type(mtr).__name__
            sid = getattr(mtr, "speech_id", None)

            if cls == "EOUMetrics":
                rec = self._rec(sid)
                rec.stt_final_ms = _ms(getattr(mtr, "transcription_delay", None))
                rec.eou_delay_ms = _ms(getattr(mtr, "end_of_utterance_delay", None))
                if rec.stt_final_ms is not None:
                    log.info(f"[LATENCY] TURN={rec.turn} STT_FINAL={rec.stt_final_ms}ms")

            elif cls == "LLMMetrics":
                rec = self._rec(sid)
                rec.llm_ttft_ms = _ms(getattr(mtr, "ttft", None))
                rec.llm_total_ms = _ms(getattr(mtr, "duration", None))
                log.info(
                    f"[LATENCY] TURN={rec.turn} LLM_TTFT={rec.llm_ttft_ms}ms "
                    f"LLM_TOTAL={rec.llm_total_ms}ms"
                )

            elif cls == "TTSMetrics":
                rec = self._rec(sid)
                ttfb = _ms(getattr(mtr, "ttfb", None))
                if rec.tts_ttfb_ms is None and ttfb is not None:
                    rec.tts_ttfb_ms = ttfb
                    log.info(f"[LATENCY] TURN={rec.turn} TTS_FIRST_BYTE={ttfb}ms")
                dur = _ms(getattr(mtr, "duration", None))
                if dur:
                    rec.tts_total_ms += dur
                # First TTS segment == agent starts speaking -> summarise the turn.
                self._summarise(sid)
        except Exception as exc:  # never break the call path on instrumentation
            log.debug("turn_latency.metrics_error", error=str(exc))

    def _summarise(self, speech_id: str | None) -> None:
        sid = speech_id or "unknown"
        rec = self._records.get(sid)
        if rec is None or rec.summarised:
            return
        rec.summarised = True

        # Attribute tool calls counted since the previous summary to this turn.
        rec.tools = self._pending_tool_count
        self._pending_tool_count = 0
        tools_kind = "none" if rec.tools == 0 else "single" if rec.tools == 1 else "multiple"

        # E2E (user speech end -> agent first audio) ~= EOU delay + LLM TTFT + TTS TTFB
        e2e_parts = [
            rec.eou_delay_ms or 0.0,
            rec.llm_ttft_ms or 0.0,
            rec.tts_ttfb_ms or 0.0,
        ]
        e2e = round(sum(e2e_parts), 1) if any(e2e_parts) else None

        def v(x: float | None) -> str:
            return f"{x}ms" if x is not None else "n/a"

        log.info(
            f"[TURN] TURN={rec.turn} "
            f"STT_FINAL_DELAY={v(rec.stt_final_ms)} "
            f"LLM_TTFT={v(rec.llm_ttft_ms)} "
            f"LLM_TOTAL={v(rec.llm_total_ms)} "
            f"TTS_FIRST_BYTE={v(rec.tts_ttfb_ms)} "
            f"TTS_TOTAL={v(round(rec.tts_total_ms, 1) if rec.tts_total_ms else None)} "
            f"E2E_USER_END_TO_AGENT_START={v(e2e)} "
            f"TOOLS={tools_kind}"
        )

    # ------------------------------------------------------------------ #
    # tool lifecycle (from `tool_execution_updated`)
    # ------------------------------------------------------------------ #
    def on_tool_update(self, ev: object) -> None:
        try:
            upd = getattr(ev, "update", None)
            if upd is None:
                return
            utype = getattr(upd, "type", "")
            if utype == "tool_call_started":
                fnc = getattr(upd, "function_call", None)
                name = getattr(fnc, "name", "unknown")
                call_id = getattr(fnc, "call_id", name)
                self._tool_starts[call_id] = (name, time.monotonic())
                self._pending_tool_count += 1
                log.info(f"[TOOL] TOOL_START {name}")
            elif utype == "tool_call_ended":
                call_id = getattr(upd, "call_id", "")
                status = getattr(upd, "status", "done")
                name, start = self._tool_starts.pop(call_id, ("unknown", None))
                dur = round((time.monotonic() - start) * 1000, 1) if start else None
                dur_s = f"{dur}ms" if dur is not None else "n/a"
                log.info(f"[TOOL] TOOL_END {name} duration={dur_s} status={status}")
        except Exception as exc:  # noqa: BLE001
            log.debug("turn_latency.tool_error", error=str(exc))

    # ------------------------------------------------------------------ #
    # tool batch count (from `function_tools_executed`)
    # ------------------------------------------------------------------ #
    def on_tools_executed(self, ev: object) -> None:
        try:
            calls = getattr(ev, "function_calls", []) or []
            n = len(calls)
            kind = "none" if n == 0 else "single" if n == 1 else "multiple"
            names = ",".join(getattr(c, "name", "?") for c in calls)
            log.info(f"[TOOL] TOOLS_EXECUTED count={n} kind={kind} names=[{names}]")
        except Exception as exc:  # noqa: BLE001
            log.debug("turn_latency.tools_executed_error", error=str(exc))

    # ------------------------------------------------------------------ #
    # granular timeline (from state/transcription events)
    # ------------------------------------------------------------------ #
    def on_user_state(self, old: str, new: str) -> None:
        if new == "speaking":
            log.info("[LATENCY] USER_SPEECH_START")
        elif old == "speaking" and new != "speaking":
            log.info("[LATENCY] USER_SPEECH_END")

    def on_agent_state(self, old: str, new: str) -> None:
        if new == "thinking":
            log.info("[LATENCY] LLM_REQUEST_START (agent thinking)")
        elif new == "speaking":
            log.info("[LATENCY] AGENT_SPEECH_START")
        elif old == "speaking" and new != "speaking":
            log.info("[LATENCY] AGENT_SPEECH_END")

    def on_stt_final(self, transcript: str) -> None:
        snippet = (transcript or "")[:80]
        log.info(f'[LATENCY] STT_FINAL_TRANSCRIPT "{snippet}"')
