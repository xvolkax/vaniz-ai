"""Live call control via LiveKit: end an in-progress call, mint a listen token.

These power the dashboard's Live Calls console. They use the same LiveKit
credentials as outbound dialing (LIVEKIT_URL / API key / secret).
"""
from __future__ import annotations

from livekit import api

from priya.config import settings
from priya.utils.logging import get_logger

log = get_logger(__name__)


def _client() -> api.LiveKitAPI:
    return api.LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )


async def end_call(room_name: str) -> None:
    """Hang up a live call by deleting its LiveKit room (drops all participants)."""
    if not room_name:
        raise RuntimeError("Call has no room to end")
    lk = _client()
    try:
        await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
        log.info("call.control.ended", room=room_name)
    finally:
        await lk.aclose()


def listen_token(room_name: str, identity: str) -> str:
    """Mint a subscribe-only LiveKit access token so a supervisor can listen in.

    The token can join the call's room and subscribe to audio, but cannot
    publish — a read-only monitor. Frontend uses livekit-client with this token.
    """
    if not room_name:
        raise RuntimeError("Call has no room to listen to")
    if not (settings.livekit_api_key and settings.livekit_api_secret):
        raise RuntimeError("LiveKit credentials not configured")
    grants = api.VideoGrants(
        room_join=True,
        room=room_name,
        can_subscribe=True,
        can_publish=False,
        can_publish_data=False,
    )
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name("Supervisor")
        .with_grants(grants)
    )
    return token.to_jwt()
