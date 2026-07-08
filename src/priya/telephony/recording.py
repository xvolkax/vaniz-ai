"""Call recording via LiveKit room-composite egress → private S3-compatible storage.

Security model: the storage bucket (Cloudflare R2 in production) stays PRIVATE.
We store only the object KEY on the call row (never a public or presigned URL).
Playback/download is served by minting short-lived presigned GET URLs on demand
(see `generate_presigned_get_url`), gated behind dashboard authentication + RBAC.

Both functions are best-effort and fully guarded — recording must never break a
live call, and presign failures degrade gracefully.
"""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from livekit import api

from priya.config import settings
from priya.utils.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_s3.client import S3Client

log = get_logger(__name__)


def _s3_configured() -> bool:
    return bool(
        settings.recording_s3_bucket
        and settings.recording_s3_access_key
        and settings.recording_s3_secret
    )


def recording_config_problems() -> list[str]:
    """Return a list of human-readable problems with the recording config.

    Empty list means recording is either disabled (nothing to validate) or fully
    configured. Used by API + worker startup to fail loud instead of silently
    returning 503 later. Only meaningful when RECORDING_ENABLED is true.
    """
    if not settings.recording_enabled:
        return []

    problems: list[str] = []
    required = (
        ("RECORDING_S3_BUCKET", settings.recording_s3_bucket),
        ("RECORDING_S3_ACCESS_KEY", settings.recording_s3_access_key),
        ("RECORDING_S3_SECRET", settings.recording_s3_secret),
    )
    missing = [name for name, val in required if not val]
    if missing:
        problems.append(f"missing/empty env: {', '.join(missing)}")

    # R2 / MinIO (and anything using path-style) require a custom endpoint.
    if settings.recording_s3_force_path_style and not settings.recording_s3_endpoint:
        problems.append(
            "RECORDING_S3_FORCE_PATH_STYLE=true but RECORDING_S3_ENDPOINT is empty"
        )

    # boto3 must be importable to mint presigned playback URLs (served by the API).
    try:
        import boto3  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        problems.append(f"boto3 not importable (pip install boto3): {exc}")

    return problems


def log_recording_config_status(component: str) -> None:
    """Log a clear, actionable line about recording configuration at startup.

    `component` is just a tag for the log (e.g. "api" / "agent")."""
    if not settings.recording_enabled:
        log.info("recording.config.disabled", component=component)
        return
    problems = recording_config_problems()
    if problems:
        log.error(
            "recording.config.incomplete",
            component=component,
            problems="; ".join(problems),
            hint="Recording is ENABLED but cannot work until these are fixed.",
        )
    else:
        log.info(
            "recording.config.ok",
            component=component,
            bucket=settings.recording_s3_bucket,
            endpoint=settings.recording_s3_endpoint or "(aws default)",
            force_path_style=settings.recording_s3_force_path_style,
        )


def recording_key_for(call_id: str) -> str:
    """Deterministic object key for a call's recording."""
    return f"recordings/{call_id}.mp4"


async def start_room_recording(room_name: str, call_id: str) -> str | None:
    """Start room-composite egress to the private bucket.

    Returns the object KEY (e.g. "recordings/<call_id>.mp4") on success, or None
    if recording is disabled/unconfigured or egress failed to start. Never raises.
    """
    if not settings.recording_enabled or not _s3_configured():
        return None

    key = recording_key_for(call_id)
    lk = api.LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )
    try:
        req = api.RoomCompositeEgressRequest(
            room_name=room_name,
            audio_only=True,
            file_outputs=[
                api.EncodedFileOutput(
                    file_type=api.EncodedFileType.MP4,
                    filepath=key,
                    s3=api.S3Upload(
                        access_key=settings.recording_s3_access_key,
                        secret=settings.recording_s3_secret,
                        bucket=settings.recording_s3_bucket,
                        region=settings.recording_s3_region or None,
                        endpoint=settings.recording_s3_endpoint or None,
                        force_path_style=settings.recording_s3_force_path_style,
                    ),
                )
            ],
        )
        await lk.egress.start_room_composite_egress(req)
        log.info("recording.started", room=room_name, call_id=call_id, key=key)
        return key
    except Exception as exc:  # noqa: BLE001 — never break the call
        log.warning("recording.start_failed", room=room_name, error=str(exc))
        return None
    finally:
        await lk.aclose()


@lru_cache(maxsize=1)
def _s3_client() -> "S3Client":
    """Build a cached S3 client for presigning against the private bucket.

    Presigning is a pure local (crypto) computation — no network call — so a
    single shared, thread-safe boto3 client is fine on the async event loop.
    `addressing_style=path` is required for Cloudflare R2 / MinIO.
    """
    import boto3
    from botocore.config import Config

    addressing = "path" if settings.recording_s3_force_path_style else "virtual"
    return boto3.client(
        "s3",
        endpoint_url=settings.recording_s3_endpoint or None,
        aws_access_key_id=settings.recording_s3_access_key,
        aws_secret_access_key=settings.recording_s3_secret,
        region_name=settings.recording_s3_region or "auto",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": addressing},
            retries={"max_attempts": 2},
        ),
    )


def generate_presigned_get_url(key: str, expires_in: int | None = None) -> str | None:
    """Mint a short-lived presigned GET URL for a private object key.

    Returns None if storage isn't configured or signing fails. Never raises.
    The credentials are used only to sign the request locally — they are never
    included in the returned URL beyond the standard SigV4 query parameters.
    """
    if not _s3_configured():
        log.warning(
            "recording.presign_skipped",
            key=key,
            reason="S3 not configured — check RECORDING_S3_BUCKET/ACCESS_KEY/SECRET on this process",
        )
        return None
    ttl = expires_in or settings.recording_url_ttl_seconds
    try:
        return _s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.recording_s3_bucket, "Key": key},
            ExpiresIn=ttl,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("recording.presign_failed", key=key, error=str(exc))
        return None
