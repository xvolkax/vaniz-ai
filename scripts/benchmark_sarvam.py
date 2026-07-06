#!/usr/bin/env python
"""Benchmark Sarvam.ai (India-hosted) — TTS (Bulbul v3) + LLM (Sarvam-M) latency.

Mirrors the other benchmark scripts. Sarvam is hosted in India, so on an
Indian deployment this should be much faster than US-based providers. Absolute
numbers here depend on where THIS script runs from.

    python scripts/benchmark_sarvam.py --runs 6
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from priya.config import settings  # noqa: E402

BASE = "https://api.sarvam.ai"
TTS_TEXT = "Namaste! Main Priya bol rahi hoon. Kya aap property mein interested hain?"
LLM_PROMPT = "Namaste, main 2BHK apartment Bangalore mein dhoond raha hoon. Budget 80 lakh."


async def tts_run(client: httpx.AsyncClient) -> float:
    """Sarvam TTS returns full base64 audio (non-streaming REST) -> total latency."""
    start = time.perf_counter()
    r = await client.post(
        f"{BASE}/text-to-speech",
        headers={
            "api-subscription-key": settings.sarvam_api_key,
            "Content-Type": "application/json",
        },
        json={
            "text": TTS_TEXT,
            "target_language_code": "hi-IN",
            "speaker": "shubh",
            "model": "bulbul:v3",
            "speech_sample_rate": 16000,
        },
    )
    elapsed = (time.perf_counter() - start) * 1000
    if r.status_code != 200:
        print(f"  [TTS] HTTP {r.status_code}: {r.text[:200]}")
        return -1
    return elapsed


async def llm_ttft(client: httpx.AsyncClient) -> float:
    """Sarvam-M via OpenAI-compatible /v1/chat/completions -> time to first token."""
    start = time.perf_counter()
    async with client.stream(
        "POST",
        f"{BASE}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.sarvam_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "sarvam-30b",
            "messages": [{"role": "user", "content": LLM_PROMPT}],
            "stream": True,
            "max_tokens": 60,
        },
    ) as resp:
        if resp.status_code != 200:
            body = await resp.aread()
            print(f"  [LLM] HTTP {resp.status_code}: {body[:200]!r}")
            return -1
        async for line in resp.aiter_lines():
            if line.startswith("data:") and "content" in line:
                return (time.perf_counter() - start) * 1000
    return (time.perf_counter() - start) * 1000


def report(label: str, samples: list[float], target_ms: float) -> None:
    ok = [s for s in samples if s > 0]
    if not ok:
        print(f"\n=== {label} === all requests failed (see errors above)")
        return
    ok.sort()
    p50 = statistics.median(ok)
    print(f"\n=== {label} ({len(ok)}/{len(samples)} ok) ===")
    print(f"min : {min(ok):7.1f} ms")
    print(f"p50 : {p50:7.1f} ms")
    print(f"max : {max(ok):7.1f} ms")
    print(f"target: < {target_ms} ms  ->  {'PASS' if p50 < target_ms else 'REVIEW'}")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=6)
    args = parser.parse_args()

    if not settings.sarvam_api_key:
        print("SARVAM_API_KEY not set in .env")
        raise SystemExit(1)

    async with httpx.AsyncClient(timeout=30) as client:
        print("Benchmarking Sarvam TTS (Bulbul v3, hi-IN)...")
        tts = [await tts_run(client) for _ in range(args.runs)]
        print("Benchmarking Sarvam LLM (Sarvam-M) TTFT...")
        llm = [await llm_ttft(client) for _ in range(args.runs)]

    report("Sarvam TTS total latency", tts, target_ms=400)
    report("Sarvam-M LLM TTFT", llm, target_ms=500)
    print("\nNote: absolute numbers reflect THIS machine's network to India.")
    print("On an India-based deployment, expect lower latency.")


if __name__ == "__main__":
    asyncio.run(main())
