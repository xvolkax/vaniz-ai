#!/usr/bin/env python
"""Benchmark Sarvam STT (Saarika / Saaras) — latency + transcript accuracy.

No local audio file needed: we synthesize a Hindi clip with Sarvam TTS (Bulbul),
then send it to Sarvam STT and measure round-trip latency + check the transcript.

    python scripts/benchmark_sarvam_stt.py --runs 5

Note: REST STT is synchronous (whole clip). This measures total request latency,
not streaming first-partial. Sarvam also has a WebSocket streaming STT for
real-time (16kHz) — that's what a live agent would use.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import statistics
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Force UTF-8 stdout so Devanagari transcripts print on Windows consoles.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from priya.config import settings  # noqa: E402

BASE = "https://api.sarvam.ai"
PHRASE = "Namaste, main do BHK apartment Bangalore mein dhoond raha hoon."


async def make_hindi_clip(client: httpx.AsyncClient) -> bytes:
    """Generate a Hindi WAV via Sarvam TTS (Bulbul v3) at 16kHz."""
    r = await client.post(
        f"{BASE}/text-to-speech",
        headers={"api-subscription-key": settings.sarvam_api_key},
        json={
            "text": PHRASE,
            "target_language_code": "hi-IN",
            "speaker": "shubh",
            "model": "bulbul:v3",
            "speech_sample_rate": 16000,
        },
    )
    r.raise_for_status()
    return base64.b64decode(r.json()["audios"][0])


async def stt_once(client: httpx.AsyncClient, wav: bytes, model: str, lang: str) -> tuple[float, str]:
    data = {"model": model}
    if lang:
        data["language_code"] = lang
    start = time.perf_counter()
    r = await client.post(
        f"{BASE}/speech-to-text",
        headers={"api-subscription-key": settings.sarvam_api_key},
        files={"file": ("clip.wav", wav, "audio/wav")},
        data=data,
    )
    elapsed = (time.perf_counter() - start) * 1000
    if r.status_code != 200:
        return -1, f"HTTP {r.status_code}: {r.text[:160]}"
    return elapsed, r.json().get("transcript", "")


async def bench_model(client, wav: bytes, model: str, lang: str, runs: int) -> None:
    samples: list[float] = []
    transcript = ""
    for _ in range(runs):
        ms, tr = await stt_once(client, wav, model, lang)
        if ms < 0:
            print(f"\n=== {model} === FAILED: {tr}")
            return
        samples.append(ms)
        transcript = tr
    samples.sort()
    print(f"\n=== Sarvam STT {model} ({len(samples)} runs) ===")
    print(f"min : {min(samples):7.1f} ms")
    print(f"p50 : {statistics.median(samples):7.1f} ms")
    print(f"max : {max(samples):7.1f} ms")
    print(f"transcript: {transcript!r}")
    print(f"spoken    : {PHRASE!r}")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    if not settings.sarvam_api_key:
        print("SARVAM_API_KEY not set"); raise SystemExit(1)

    async with httpx.AsyncClient(timeout=40) as client:
        print("Generating Hindi test clip via Sarvam TTS...")
        wav = await make_hindi_clip(client)
        print(f"clip size: {len(wav)} bytes")

        # saarika = pure transcription (keeps spoken language); needs language_code.
        await bench_model(client, wav, "saarika:v2.5", "hi-IN", args.runs)
        # saaras:v3 = latest ASR; auto language detect (unknown), transcribe mode.
        await bench_model(client, wav, "saaras:v3", "unknown", args.runs)

    print("\nNote: REST STT = whole-clip synchronous latency (not streaming first-partial).")
    print("Absolute numbers reflect THIS machine's network to India; India deploy = lower.")


if __name__ == "__main__":
    asyncio.run(main())
