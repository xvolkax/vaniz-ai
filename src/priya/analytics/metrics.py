"""Prometheus-compatible metrics.

Exposed on the API service /metrics endpoint. Histograms use buckets tuned for
sub-second voice targets (STT<300ms, LLM<500ms, TTS<300ms, E2E<1000ms).
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

_LATENCY_BUCKETS = (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)

# ---- Latency (seconds) ----
STT_LATENCY = Histogram(
    "priya_stt_latency_seconds", "Deepgram STT end-of-utterance latency", buckets=_LATENCY_BUCKETS
)
LLM_LATENCY = Histogram(
    "priya_llm_latency_seconds", "GPT-4o-mini time-to-first-token", buckets=_LATENCY_BUCKETS
)
TTS_LATENCY = Histogram(
    "priya_tts_latency_seconds", "Cartesia time-to-first-audio-byte", buckets=_LATENCY_BUCKETS
)
E2E_LATENCY = Histogram(
    "priya_e2e_latency_seconds",
    "End-to-end user-stopped-speaking to agent-first-audio",
    buckets=_LATENCY_BUCKETS,
)

# ---- Counters ----
CALLS_TOTAL = Counter("priya_calls_total", "Total calls handled", ["direction", "outcome"])
INTERRUPTIONS_TOTAL = Counter("priya_interruptions_total", "Total user interruptions (barge-in)")
LEADS_QUALIFIED = Counter("priya_leads_qualified_total", "Leads reaching qualified status")
APPOINTMENTS_BOOKED = Counter(
    "priya_appointments_booked_total", "Appointments booked", ["type"]
)
TOOL_CALLS = Counter("priya_tool_calls_total", "Function tool invocations", ["tool"])
ERRORS_TOTAL = Counter("priya_errors_total", "Errors in the call path", ["stage"])

# ---- Gauges ----
ACTIVE_CALLS = Gauge("priya_active_calls", "Currently active calls")
