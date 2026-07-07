"""Call recording via LiveKit room-composite egress → S3-compatible storage.

Best-effort and fully guarded: only used when RECORDING_ENABLED and S3 settings
are present. Returns the predictable public URL of the recording file (the file
is finalized by LiveKit after the call ends) so it can be stored on the call row
immediately.
"""
from __future__ import annotations

from livekit import api

from priya.config import settings
from priya.utils.logging import get_logger

log = get_logger(__name__)


def _s3_configured() -> bool:
    return bool(
        settings.recording_s3_bucket
        and settings.recording_s3_access_key
        and settings.recording_s3_secret
    )


async def start_room_recording(room_name: str, call_id: str) -> str | None:
    """Start room-composite egress to S3. Returns the public recording URL or None.

    Never raises — recording must never break a live call.
    """
    if not settings.recording_enabled or not _s3_configured():
        return None

    key = f"recordings/{call_id}.mp4"
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
                    ),
                )
            ],
        )
        await lk.egress.start_room_composite_egress(req)
        base = settings.recording_public_base_url.rstrip("/")
        url = f"{base}/{key}" if base else key
        log.info("recording.started", room=room_name, call_id=call_id, url=url)
        return url
    except Exception as exc:  # noqa: BLE001 — never break the call
        log.warning("recording.start_failed", room=room_name, error=str(exc))
        return None
    finally:
        await lk.aclose()
