"""FastAPI control-plane service.

Responsibilities (separate from the LiveKit agent worker process):
  * /healthz, /readyz  — liveness & readiness (checks DB).
  * /metrics           — Prometheus exposition.
  * /calls/outbound    — trigger an outbound call (bearer-auth + rate limited).

The agent worker runs as its own process (`priya.agent.worker`). This service
is the ops/API surface.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from priya import __version__
from priya.api.routers import analytics as analytics_router
from priya.api.routers import auth as auth_router
from priya.api.routers import calls as calls_router
from priya.api.routers import campaigns as campaigns_router
from priya.api.routers import dashboard as dashboard_router
from priya.api.routers import leads as leads_router
from priya.api.routers import properties as properties_router
from priya.api.routers import tenants as tenants_router
from priya.api.routers import users as users_router
from priya.api.schemas import (
    HealthResponse,
    OutboundCallRequest,
    OutboundCallResponse,
)
from priya.auth.dependencies import CurrentUser, require_role
from priya.campaigns import engine as campaign_engine
from priya.config import settings
from priya.db.database import dispose_db, get_engine, init_db
from priya.db.models import UserRole
from priya.telephony.outbound import place_outbound_call
from priya.telephony.recording import log_recording_config_status
from priya.utils.logging import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if settings.app_env == "development":
        await init_db()  # convenience; production uses Alembic migrations
    if settings.campaign_resume_on_startup:
        try:
            await campaign_engine.resume_running()
        except Exception as exc:  # noqa: BLE001 — never block startup on this
            log.warning("api.campaign_resume.error", error=str(exc))
    # Fail loud (in logs) if recording is enabled but misconfigured, so the
    # opaque 503 on /calls/{id}/recording has a clear root cause at startup.
    log_recording_config_status("api")
    log.info("api.startup", version=__version__, region=settings.service_region)
    yield
    await campaign_engine.shutdown()
    await dispose_db()
    log.info("api.shutdown")


app = FastAPI(title="Priya Voice Agent API", version=__version__, lifespan=lifespan)

# SaaS control-plane routers (JWT-authenticated, tenant-scoped).
app.include_router(auth_router.router)
app.include_router(tenants_router.router)
app.include_router(users_router.router)
app.include_router(properties_router.router)
app.include_router(leads_router.router)
app.include_router(calls_router.router)
app.include_router(dashboard_router.router)
app.include_router(analytics_router.router)
app.include_router(campaigns_router.router)


# --------------------------------------------------------------------------- #
# Lightweight in-memory rate limiter (per-token, sliding window).
# For multi-replica deployments, swap for Redis-backed limiting.
# --------------------------------------------------------------------------- #
_RATE_LIMIT = 20          # requests
_RATE_WINDOW = 60.0       # seconds
_hits: dict[str, deque[float]] = defaultdict(deque)


def _rate_limit(key: str) -> None:
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > _RATE_WINDOW:
        q.popleft()
    if len(q) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )
    q.append(now)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(
        status="ok", version=__version__, db="unchecked", region=settings.service_region
    )


@app.get("/readyz", response_model=HealthResponse)
async def readyz() -> HealthResponse:
    db_status = "ok"
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {exc}"[:80]
        raise HTTPException(status_code=503, detail=f"DB not ready: {db_status}") from exc
    return HealthResponse(
        status="ready", version=__version__, db=db_status, region=settings.service_region
    )


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post(
    "/calls/outbound",
    response_model=OutboundCallResponse,
)
async def trigger_outbound(
    payload: OutboundCallRequest,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
) -> OutboundCallResponse:
    _rate_limit(str(user.tenant_id))
    log.info("api.outbound.request", phone=payload.phone_number, tenant=str(user.tenant_id))
    try:
        result = await place_outbound_call(
            payload.phone_number, payload.lead_name, tenant_id=str(user.tenant_id)
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.error("api.outbound.error", error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to place call") from exc
    return OutboundCallResponse(**result)
