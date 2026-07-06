#!/usr/bin/env python
"""End-to-end voice latency estimator — target < 1000 ms.

Combines measured STT + LLM + TTS stage latencies into an estimated end-to-end
response time (user stops speaking -> agent first audio byte), adding a fixed
network/turn-detection budget. For true wall-clock E2E, use the live Prometheus
`priya_e2e_latency_seconds` histogram emitted during real calls.

    python scripts/benchmark_e2e.py --runs 10
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import benchmark_llm  # noqa: E402
import benchmark_tts  # noqa: E402
import httpx  # noqa: E402

# Fixed budgets (ms): turn-detector endpointing + network legs.
TURN_DETECTION_BUDGET = 250
NETWORK_BUDGET = 80


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=10)
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=30) as client:
        llm_samples = [await benchmark_llm.one_run(client) for _ in range(args.runs)]
        tts_samples = [await benchmark_tts.one_run(client) for _ in range(args.runs)]

    llm_p50 = sorted(llm_samples)[len(llm_samples) // 2]
    tts_p50 = sorted(tts_samples)[len(tts_samples) // 2]
    est = TURN_DETECTION_BUDGET + llm_p50 + tts_p50 + NETWORK_BUDGET

    print("\n=== Estimated End-to-End Voice Latency ===")
    print(f"turn detection budget : {TURN_DETECTION_BUDGET:6.0f} ms")
    print(f"LLM TTFT (p50)        : {llm_p50:6.1f} ms")
    print(f"TTS TTFB (p50)        : {tts_p50:6.1f} ms")
    print(f"network budget        : {NETWORK_BUDGET:6.0f} ms")
    print(f"------------------------------------------")
    print(f"estimated E2E         : {est:6.1f} ms")
    print(f"target: < 1000 ms  ->  {'PASS' if est < 1000 else 'REVIEW'}")


if __name__ == "__main__":
    asyncio.run(main())
