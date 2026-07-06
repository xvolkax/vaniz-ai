#!/usr/bin/env python
"""Benchmark GPT-4o-mini time-to-first-token (TTFT) — target < 500 ms.

Measures streaming TTFT over N runs from the Bangalore/Singagpore egress.

    python scripts/benchmark_llm.py --runs 10
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

PROMPT = "Namaste, main 2BHK apartment Bangalore mein dhoond raha hoon. Budget 80 lakh."


async def one_run(client: httpx.AsyncClient) -> float:
    start = time.perf_counter()
    async with client.stream(
        "POST",
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={
            "model": settings.openai_model,
            "messages": [{"role": "user", "content": PROMPT}],
            "stream": True,
            "max_tokens": 60,
        },
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if line.startswith("data:") and "content" in line:
                return (time.perf_counter() - start) * 1000
    return (time.perf_counter() - start) * 1000


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=10)
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=30) as client:
        samples = [await one_run(client) for _ in range(args.runs)]

    _report("LLM TTFT", samples, target_ms=500)


def _report(label: str, samples: list[float], target_ms: float) -> None:
    samples.sort()
    p50 = statistics.median(samples)
    p95 = samples[int(len(samples) * 0.95) - 1]
    print(f"\n=== {label} ({len(samples)} runs) ===")
    print(f"min : {min(samples):7.1f} ms")
    print(f"p50 : {p50:7.1f} ms")
    print(f"p95 : {p95:7.1f} ms")
    print(f"max : {max(samples):7.1f} ms")
    print(f"target: < {target_ms} ms  ->  {'PASS' if p50 < target_ms else 'REVIEW'}")


if __name__ == "__main__":
    asyncio.run(main())
