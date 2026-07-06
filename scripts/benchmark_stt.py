#!/usr/bin/env python
"""Benchmark Deepgram Nova-3 streaming STT latency — target < 300 ms.

Streams a local 16kHz mono WAV/PCM file to Deepgram's realtime endpoint and
measures the delay between the last audio chunk sent and the final transcript.

    python scripts/benchmark_stt.py --audio sample_hindi.wav
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import wave
from pathlib import Path

import httpx  # noqa: F401  (kept for parity; websockets used below)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from priya.config import settings  # noqa: E402

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    raise


async def run(audio_path: str) -> None:
    url = (
        "wss://api.deepgram.com/v1/listen?"
        f"model={settings.deepgram_model}&language={settings.deepgram_language}"
        "&interim_results=true&punctuate=true&smart_format=true"
        "&encoding=linear16&sample_rate=16000&channels=1"
    )
    headers = {"Authorization": f"Token {settings.deepgram_api_key}"}

    with wave.open(audio_path, "rb") as wf:
        frames = wf.readframes(wf.getnframes())

    chunk = 3200  # 100ms @ 16kHz 16-bit mono
    last_audio_ts = 0.0
    final_ts = 0.0

    async with websockets.connect(url, extra_headers=headers) as ws:

        async def sender() -> None:
            nonlocal last_audio_ts
            for i in range(0, len(frames), chunk):
                await ws.send(frames[i : i + chunk])
                last_audio_ts = time.perf_counter()
                await asyncio.sleep(0.1)  # real-time pacing
            await ws.send(json.dumps({"type": "CloseStream"}))

        async def receiver() -> None:
            nonlocal final_ts
            async for message in ws:
                data = json.loads(message)
                if data.get("is_final") and data.get("channel"):
                    alt = data["channel"]["alternatives"][0]
                    if alt.get("transcript"):
                        final_ts = time.perf_counter()

        await asyncio.gather(sender(), receiver())

    latency_ms = (final_ts - last_audio_ts) * 1000 if final_ts and last_audio_ts else -1
    print("\n=== Deepgram Nova-3 STT latency ===")
    print(f"final-transcript delay: {latency_ms:7.1f} ms")
    print(f"target: < 300 ms  ->  {'PASS' if 0 < latency_ms < 300 else 'REVIEW'}")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, help="16kHz mono WAV file")
    args = parser.parse_args()
    await run(args.audio)


if __name__ == "__main__":
    asyncio.run(main())
