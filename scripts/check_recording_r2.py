"""Local self-test for the recording → R2 pipeline (run before deploying).

What it does (against the REAL bucket configured in .env):
  1. Validates recording config + boto3 availability.
  2. Uploads a tiny test object to  recordings/_selftest_<ts>.mp4
  3. Mints a presigned GET URL (exactly like the API endpoint does).
  4. Fetches that URL over HTTP and checks the bytes round-trip.
  5. Deletes the test object.

No LiveKit call, no DB, no API server needed. Prints PASS/FAIL per step.

Usage (from repo root):
    .venv\\Scripts\\python.exe scripts\\check_recording_r2.py
"""
from __future__ import annotations

import os
import sys
import time
import urllib.request
from pathlib import Path

# Ensure settings load the repo-root .env regardless of the caller's CWD.
_REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(_REPO_ROOT)
sys.path.insert(0, str(_REPO_ROOT / "src"))

from priya.config import settings  # noqa: E402
from priya.telephony.recording import (  # noqa: E402
    _s3_client,
    generate_presigned_get_url,
    recording_config_problems,
)


def _ok(msg: str) -> None:
    print(f"  [PASS] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def main() -> int:
    print("== Recording → R2 self-test ==")
    print(f"  bucket           = {settings.recording_s3_bucket}")
    print(f"  endpoint         = {settings.recording_s3_endpoint}")
    print(f"  region           = {settings.recording_s3_region}")
    print(f"  force_path_style = {settings.recording_s3_force_path_style}")
    print(f"  enabled          = {settings.recording_enabled}")

    # 1) Config validation
    problems = recording_config_problems()
    if problems:
        _fail("config incomplete: " + "; ".join(problems))
        return 1
    _ok("config + boto3 OK")

    key = f"recordings/_selftest_{int(time.time())}.mp4"
    payload = b"priya-r2-selftest"
    client = _s3_client()

    # 2) Upload
    try:
        client.put_object(
            Bucket=settings.recording_s3_bucket,
            Key=key,
            Body=payload,
            ContentType="audio/mp4",
        )
        _ok(f"uploaded test object: {key}")
    except Exception as exc:  # noqa: BLE001
        _fail(f"put_object failed (check creds/bucket/token perms): {exc}")
        return 1

    # 3) Presign
    url = generate_presigned_get_url(key, expires_in=120)
    if not url:
        _fail("presign returned None")
        _cleanup(client, key)
        return 1
    _ok("presigned GET URL generated")
    print(f"       {url[:130]}...")

    # 4) Fetch over HTTP (proves R2 accepts the signature; no auth header needed)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:  # noqa: S310
            body = resp.read()
            status = resp.status
        if status == 200 and body == payload:
            _ok(f"fetched via presigned URL (HTTP {status}, {len(body)} bytes, bytes match)")
        else:
            _fail(f"unexpected fetch result: HTTP {status}, {len(body)} bytes")
            _cleanup(client, key)
            return 1
    except Exception as exc:  # noqa: BLE001
        _fail(f"presigned fetch failed: {exc}")
        _cleanup(client, key)
        return 1

    # 5) Cleanup
    _cleanup(client, key)
    print("\n== RESULT: ALL CHECKS PASSED — R2 recording pipeline works ==")
    return 0


def _cleanup(client, key: str) -> None:  # noqa: ANN001
    try:
        client.delete_object(Bucket=settings.recording_s3_bucket, Key=key)
        _ok(f"deleted test object: {key}")
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] could not delete {key}: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
