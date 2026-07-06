"""Pluggable STT factory — switch providers via STT_PROVIDER without code edits.

  * sarvam   : Saaras v3 (India-hosted, Hindi-native), native WS streaming  [best Hindi/Hinglish]
  * deepgram : Nova-3 multi (Hindi-English code-mix), streaming             [lower latency, weaker Hindi]

Both expose LiveKit's streaming STT interface, so the AgentSession uses them
identically. Nothing is removed: set STT_PROVIDER=deepgram|sarvam to switch.
"""
from __future__ import annotations

from livekit.agents import stt as stt_base
from livekit.plugins import deepgram

from priya.config import settings
from priya.utils.logging import get_logger

log = get_logger(__name__)


def build_stt() -> stt_base.STT:
    provider = settings.stt_provider.lower()

    if provider == "sarvam":
        from livekit.plugins import sarvam

        log.info(
            "stt.provider.sarvam",
            model=settings.sarvam_stt_model,
            language=settings.sarvam_stt_language,
            mode=settings.sarvam_stt_mode,
        )
        return sarvam.STT(
            language=settings.sarvam_stt_language,   # e.g. hi-IN
            model=settings.sarvam_stt_model,          # saarika:v2.5 | saaras:v3
            mode=settings.sarvam_stt_mode,            # transcribe (saaras:v3)
            api_key=settings.sarvam_api_key,
        )

    # default: Deepgram Nova-3 (multilingual, streaming, interim results)
    log.info("stt.provider.deepgram", model=settings.deepgram_model)
    return deepgram.STT(
        model=settings.deepgram_model,
        language=settings.deepgram_language,
        interim_results=True,
        punctuate=True,
        smart_format=True,
    )
