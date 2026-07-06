"""Per-call latency tracker.

Consumes LiveKit `metrics_collected` events (STT/LLM/TTS/EOU) and both:
  * records to Prometheus histograms, and
  * accumulates per-call averages persisted to the `calls` table on hangup.

LiveKit 1.x emits typed metrics: STTMetrics, LLMMetrics, TTSMetrics,
EOUMetrics. We map them to our four target stages.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from priya.analytics import metrics as m
from priya.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class _Accumulator:
    total: float = 0.0
    count: int = 0

    def add(self, value: float) -> None:
        if value is None or value < 0:
            return
        self.total += value
        self.count += 1

    @property
    def avg_ms(self) -> float | None:
        return round((self.total / self.count) * 1000, 2) if self.count else None


@dataclass
class LatencyTracker:
    """Aggregates latency for a single call."""

    call_id: str
    stt: _Accumulator = field(default_factory=_Accumulator)
    llm: _Accumulator = field(default_factory=_Accumulator)
    tts: _Accumulator = field(default_factory=_Accumulator)
    e2e: _Accumulator = field(default_factory=_Accumulator)
    interruptions: int = 0

    def on_livekit_metrics(self, ev_metrics: object) -> None:
        """Handle a LiveKit metrics object (duck-typed by attribute)."""
        cls = type(ev_metrics).__name__

        try:
            if cls == "STTMetrics":
                # For streaming STT `duration` is 0.0 (websocket). The meaningful
                # STT-final latency is EOUMetrics.transcription_delay (handled below).
                dur = getattr(ev_metrics, "duration", None)
                if dur and dur > 0:
                    self._record("stt", dur, m.STT_LATENCY)
            elif cls == "LLMMetrics":
                ttft = getattr(ev_metrics, "ttft", None)
                self._record("llm", ttft, m.LLM_LATENCY)
            elif cls == "TTSMetrics":
                ttfb = getattr(ev_metrics, "ttfb", None)
                self._record("tts", ttfb, m.TTS_LATENCY)
            elif cls == "EOUMetrics":
                # transcription_delay = time to final transcript after speech end
                # (the true STT-final latency for streaming STT).
                transcription_delay = getattr(ev_metrics, "transcription_delay", None)
                if transcription_delay:
                    self._record("stt", transcription_delay, m.STT_LATENCY)
                # end_of_utterance_delay ~ endpointing + transcription completion
                delay = getattr(ev_metrics, "end_of_utterance_delay", None)
                self._record("e2e", delay, m.E2E_LATENCY)
        except Exception as exc:  # never break the call path on metrics
            log.warning("latency.metrics.error", error=str(exc), metric_type=cls)

    def _record(self, stage: str, value: float | None, hist) -> None:
        if value is None:
            return
        acc: _Accumulator = getattr(self, stage)
        acc.add(value)
        hist.observe(value)
        log.debug("latency.sample", call_id=self.call_id, stage=stage, seconds=round(value, 4))

    def record_interruption(self) -> None:
        self.interruptions += 1
        m.INTERRUPTIONS_TOTAL.inc()

    def as_call_fields(self) -> dict[str, float | int | None]:
        return {
            "avg_stt_latency_ms": self.stt.avg_ms,
            "avg_llm_latency_ms": self.llm.avg_ms,
            "avg_tts_latency_ms": self.tts.avg_ms,
            "avg_e2e_latency_ms": self.e2e.avg_ms,
            "user_interruptions": self.interruptions,
        }
