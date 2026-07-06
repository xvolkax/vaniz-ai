#!/usr/bin/env python
"""Benchmark Cartesia time-to-first-audio-byte (TTFB) — target < 300 ms.

    python scripts/benchmark_tts.py --runs 10
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

TEXT = "Namaste! Main Priya bol rahi hoon. Kya aap property mein interested hain?"


async def one_run(client: httpx.AsyncClient) -> float:
    start = time.perf_counter()
    async with client.stream(
        "POST",
        "https://api.cartesia.ai/tts/bytes",
        headers={
            "X-API-Key": settings.cartesia_api_key,
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json",
        },
        json={
            "model_id": settings.cartesia_model,
            "transcript": TEXT,
            "voice": {"mode": "id", "id": settings.cartesia_voice_id},
            "language": settings.cartesia_language,
            "output_format": {
                "container": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": 16000,
            },
        },
    ) as resp:
        resp.raise_for_status()
        async for chunk in resp.aiter_bytes():
            if chunk:
                return (time.perf_counter() - start) * 1000
    return (time.perf_counter() - start) * 1000


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=10)
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=30) as client:
        samples = [await one_run(client) for _ in range(args.runs)]

    samples.sort()
    p50 = statistics.median(samples)
    print(f"\n=== Cartesia TTS TTFB ({len(samples)} runs) ===")
    print(f"min : {min(samples):7.1f} ms")
    print(f"p50 : {p50:7.1f} ms")
    print(f"max : {max(samples):7.1f} ms")
    print(f"target: < 300 ms  ->  {'PASS' if p50 < 300 else 'REVIEW'}")


if __name__ == "__main__":
    asyncio.run(main())
