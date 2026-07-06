# Priya — Multi-Tenant AI Calling Platform for Real-Estate

A **SaaS voice platform**: a Hindi-first, low-latency LiveKit voice agent that
qualifies leads and books site visits, plus a **multi-tenant control-plane API**
and a **broker dashboard** for managing leads, properties, calls, campaigns and
analytics.

```
Voice path:
  Caller ⇄ Vobiz SIP ⇄ LiveKit ⇄ [ STT (Deepgram/Sarvam) → LLM → Cartesia TTS ]
                                    + Silero VAD + Multilingual Turn Detector

Control plane:
  Broker Dashboard (React) ─HTTPS→ Caddy ─/api→ FastAPI (JWT, tenant-scoped)
                                                    ↳ PostgreSQL (async SQLAlchemy)
                                                    ↳ Campaign engine → outbound calls
```

Every broker is an isolated **tenant**. Users authenticate with **JWT**; all
data (leads, properties, calls, campaigns, appointments) is scoped by
`tenant_id`. The agent serves each tenant's own property catalog from the DB.

---

## Components

### 1. Voice agent (`src/priya/agent`)
- Streaming STT → LLM → TTS on the non-deprecated LiveKit 1.x `AgentSession`
  API, with `@function_tool` + `RunContext`.
- Hindi-English code-mix; semantic MultilingualModel turn detector over Silero VAD.
- Explicit state machine: greeting → qualification → requirements → budget →
  timeline → booking → summary → completion.
- Tools: lead update, **dynamic DB-backed property lookup**, site-visit /
  callback / agent-transfer booking (calendar conflict detection), warm human
  transfer, and call finalization.
- On finalize, the call outcome is reconciled back onto the lead and (if part of
  a campaign) the `CampaignTarget`.

### 2. Control-plane API (`src/priya/api`)
FastAPI, JWT-authenticated, fully tenant-scoped. Routers grouped by module under
`src/priya/api/routers`.

### 3. Broker dashboard (`frontend/`)
React + TypeScript + Tailwind + TanStack Query + React Router. Pages: Dashboard,
Leads, Properties, Calls, Campaigns, Appointments, Analytics, Settings. See
`frontend/README.md`.

---

## Multi-tenancy & auth

- **Tenants** (`tenants`) are the isolation boundary; every operational table
  (`leads`, `calls`, `appointments`, `properties`, `campaigns`, …) carries a
  `tenant_id`.
- **Users** (`users`) belong to a tenant with a role. RBAC is hierarchical:
  `owner > admin > agent > viewer`.
- **JWT**: bcrypt password hashing + PyJWT tokens embedding `sub`, `tenant_id`
  and `role`. Every request resolves the tenant from the token — never from the
  client — guaranteeing data isolation. A `401` clears the session.
- Config: `JWT_SECRET` (required, ≥32 bytes in prod), `JWT_ALGORITHM`,
  `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `ALLOW_PUBLIC_SIGNUP`.

---

## API surface

All endpoints except health/metrics require `Authorization: Bearer <JWT>` and
are scoped to the caller's tenant.

| Module | Endpoints |
|--------|-----------|
| Auth | `POST /auth/register` (tenant + owner), `POST /auth/login`, `GET /auth/me` |
| Tenants | `GET /tenants/me`, `PATCH /tenants/me` (admin+) |
| Users | `GET /users`, `POST /users`, `PATCH /users/{id}`, `DELETE /users/{id}` (admin+) |
| Properties | `GET/POST /properties`, `GET/PATCH /properties/{id}`, `DELETE /properties/{id}` (admin+) |
| Leads | `GET/POST /leads`, `GET /leads/export` (CSV), `POST /leads/import` (CSV), `GET/PATCH /leads/{id}`, `DELETE /leads/{id}` (admin+) |
| Calls | `GET /calls`, `GET /calls/{id}`, `POST /calls/outbound` (agent+) |
| Dashboard | `GET /dashboard/summary` |
| Analytics | `GET /analytics/overview`, `/call-outcomes`, `/lead-sources`, `/conversion-trends` |
| Campaigns | `GET/POST /campaigns`, `GET /campaigns/{id}`, `POST /campaigns/{id}/leads`, `.../start` `.../pause` `.../resume` `.../stop`, `GET /campaigns/{id}/analytics` |
| Ops | `GET /healthz`, `GET /readyz`, `GET /metrics` |

Leads support filtering (status, source, qualification-score range, date range,
search), pagination and sorting. Calls support filtering (outcome, date range,
duration, lead, campaign, search) with eager-loaded lead + summary.

---

## Properties (DB-backed knowledge)

Each tenant's projects live in the `properties` table and are managed via the
dashboard/API. During a call the agent reads the tenant's **live** catalog from
the DB (`lookup_properties` tool + a per-call rendered prompt), so dashboard
edits are reflected on the next call — no restart, no `project.yaml`.

Set `KNOWLEDGE_SOURCE=db` (default). To seed a tenant from the legacy YAML:
```bash
python scripts/migrate_yaml_to_db.py --slug my-brokerage \
  --owner-email owner@example.com --owner-password 'ChangeThis123' --phone +91XXXXXXXXXX
```

---

## Campaign engine (`src/priya/campaigns`)

Bulk outbound calling on top of the single-call engine, per tenant:
- Configurable **concurrency**, **retry** count, **retry delay** (backoff), and
  **working hours** (IST).
- Targets are claimed with `SELECT … FOR UPDATE SKIP LOCKED` (safe across
  workers), dialed via `place_outbound_call`, and reconciled from the finalized
  call outcome — `CampaignTarget` is the source of truth for campaign analytics
  (attempted / connected / interested / callbacks / site-visits / conversion).
- Lifecycle: draft → running → paused → completed/failed. Running campaigns
  resume automatically after an API restart (`CAMPAIGN_RESUME_ON_STARTUP`).

---

## Latency targets

| Stage | Target |
|-------|--------|
| STT | < 300 ms |
| LLM TTFT | < 500 ms |
| TTS TTFB | < 300 ms |
| End-to-end | < 1000 ms |

Live latency is exported at `/metrics` (`priya_*_latency_seconds`) and stored
per call.

---

## Project structure

```
priya-voice-agent/
├── src/priya/
│   ├── config.py               # pydantic-settings, all env-driven
│   ├── auth/                   # JWT security + FastAPI deps (RBAC, tenant scope)
│   ├── agent/                  # voice agent (worker, tools, prompts, completion)
│   ├── campaigns/              # outbound campaign execution engine
│   ├── telephony/              # Vobiz SIP (inbound trunk, outbound, dispatch)
│   ├── knowledge/              # retrieval abstraction (markdown / vector-ready)
│   ├── crm/ · calendar/ · whatsapp/   # pluggable adapters
│   ├── db/                     # async SQLAlchemy models + repositories
│   ├── analytics/              # Prometheus metrics + latency tracker
│   └── api/
│       ├── main.py             # app wiring (routers, lifespan, engine startup)
│       ├── schemas.py          # Pydantic request/response models
│       └── routers/            # auth, tenants, users, properties, leads,
│                               #   calls, dashboard, analytics, campaigns
├── frontend/                   # React broker dashboard (Vite + TS + Tailwind)
├── scripts/                    # setup_sip, migrate_yaml_to_db, benchmarks, ...
├── migrations/                 # Alembic (async) — 0001..0006
├── deploy/                     # Caddy/nginx, systemd, DigitalOcean setup
├── tests/                      # pytest
├── Dockerfile / docker-compose.yml / Makefile
└── ARCHITECTURE.md / DEPLOYMENT.md
```

Data model: `tenants`, `users`, `properties`, `leads`, `calls`,
`conversation_summaries`, `appointments`, `audit_logs`, `campaigns`,
`campaign_targets`.

---

## Local development

Prereqs: Python 3.11+, Node 20+, Docker (for Postgres), and API keys for
LiveKit, Deepgram/Sarvam, OpenAI, Cartesia.

### Backend
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env         # fill in credentials + a strong JWT_SECRET
make dev-db                  # local Postgres in Docker
make migrate                 # alembic upgrade head  (or: make init-db)
make setup-sip               # provision Vobiz SIP (once) → copy IDs into .env

# two terminals
make run-agent               # LiveKit worker
make run-api                 # FastAPI control plane on :8080
```

### Frontend
```bash
cd frontend
npm install
npm run dev                  # http://localhost:5173 (proxies /api → :8080)
```

### Auth flow (get a JWT, then call the API)
```bash
# Register the first organization (returns a token). Disable ALLOW_PUBLIC_SIGNUP after.
curl -X POST http://localhost:8080/auth/register -H "Content-Type: application/json" \
  -d '{"tenant_name":"Acme Realty","tenant_slug":"acme","email":"owner@acme.com","password":"change-me-123"}'

# Or log in:
TOKEN=$(curl -s -X POST http://localhost:8080/auth/login -H "Content-Type: application/json" \
  -d '{"email":"owner@acme.com","password":"change-me-123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Use the JWT (tenant-scoped). Example: trigger an outbound call.
curl -X POST http://localhost:8080/calls/outbound \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"phone_number":"+9198XXXXXXXX","lead_name":"Rahul"}'
```

---

## Testing & benchmarks

```bash
make test          # pytest (state machine, scoring, completion, knowledge, factories)
make lint          # ruff + mypy
make bench-llm     # GPT-4o-mini TTFT
make bench-tts     # Cartesia TTFB
make bench-e2e     # estimated end-to-end
```

---

## Docker

```bash
docker compose up -d --build   # postgres + migrate + agent + api + web (dashboard)
docker compose logs -f web api agent
docker compose up -d --scale agent=3   # scale voice workers
```

Production (domain + automatic HTTPS via Caddy) is documented in
`DEPLOYMENT.md` (section 8).

---

## Security

- **JWT auth** (bcrypt hashing + PyJWT); tokens carry tenant + role. Every
  request is tenant-scoped from the token; RBAC enforced per endpoint.
- **Multi-tenant isolation**: all queries filter by `tenant_id`; a user can
  never read or mutate another tenant's data.
- `JWT_SECRET` must be a long random value in production. Set
  `ALLOW_PUBLIC_SIGNUP=false` after creating your first tenant.
- **TLS** terminates at Caddy (automatic Let's Encrypt); the API binds to
  localhost behind the proxy. Voice/SIP media goes directly to LiveKit.
- `/metrics` should be restricted to your monitoring network.
- Pydantic validation (E.164 phone, etc.); non-root Docker user; systemd
  hardening for the bare-metal path.
