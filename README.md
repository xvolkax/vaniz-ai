# Priya — Hindi-first AI Calling Agent for Indian Real-Estate

Production-ready, low-latency voice agent built on the **latest LiveKit Agents
(1.5+) architecture**. Priya handles inbound and outbound real-estate calls in
**Hindi and English**, qualifies leads, and books site visits — with natural
interruption handling and sub-second response targets.

```
Caller ⇄ Vobiz SIP ⇄ LiveKit ⇄ [ Deepgram Nova-3 → GPT-4o-mini → Cartesia Sonic ]
                                   + Silero VAD + Multilingual Turn Detector
```

## Highlights

- **Streaming everywhere**: STT, LLM and TTS all stream; nothing waits for full sentences.
- **Non-deprecated LiveKit APIs**: `AgentSession` + `turn_handling=TurnHandlingOptions(...)`,
  `@function_tool`, `RunContext`. No deprecated classes.
- **Hindi-English code-mix**: Deepgram Nova-3 `language="multi"`, Cartesia Hindi voice,
  and the semantic **MultilingualModel** turn detector layered over Silero VAD.
- **Barge-in / interruptions**: enabled and tracked per call.
- **Explicit conversation state machine**: greeting → qualification → requirements →
  budget → timeline → booking → summary → completion.
- **Function tools**: lead create/update, knowledge lookup, site-visit / callback /
  agent-transfer booking (with calendar conflict detection), and call finalization.
- **Async PostgreSQL** (SQLAlchemy 2.0 + asyncpg) off the audio hot-path.
- **Observability**: structured JSON logs + Prometheus metrics (STT/LLM/TTS/E2E latency,
  interruptions, conversion, booking rate, outcome).
- **Pluggable adapters** (Phase 2 ready): CRM (Zoho/HubSpot/Salesforce), WhatsApp
  follow-up, and RAG/vector DB — all behind clean interfaces.

## Latency targets

| Stage | Target | How |
|-------|--------|-----|
| STT (Deepgram Nova-3) | < 300 ms | streaming, interim results, `endpointing_ms=25` |
| LLM (GPT-4o-mini) | < 500 ms TTFT | streaming, preemptive generation |
| TTS (Cartesia Sonic) | < 300 ms TTFB | streaming, first-byte playback |
| End-to-end | < 1000 ms | tuned endpointing + preemptive generation + BLR/SGP region |

## Project structure

```
priya-voice-agent/
├── src/priya/
│   ├── config.py               # pydantic-settings, all env-driven
│   ├── agent/                  # the voice agent (Phase 1 core)
│   │   ├── worker.py           # LiveKit worker entrypoint + pipeline
│   │   ├── assistant.py        # PriyaAgent (persona + tools)
│   │   ├── prompts.py          # persona prompt + per-state guidance
│   │   ├── state.py            # conversation state machine + lead scoring
│   │   ├── context.py          # per-call runtime context (userdata)
│   │   ├── tools.py            # lead/knowledge function tools
│   │   ├── booking_tools.py    # site-visit / callback / transfer tools
│   │   ├── completion.py       # summary, scoring, finalize + follow-up
│   │   └── completion_tools.py # finalize_call tool
│   ├── telephony/              # Vobiz SIP (inbound trunk, outbound, dispatch)
│   ├── stt/llm/tts             # provided by LiveKit plugins (no custom code)
│   ├── knowledge/              # retrieval abstraction (markdown → vector-ready)
│   ├── crm/                    # adapter pattern (noop + Zoho/HubSpot/SF stubs)
│   ├── calendar/               # DB calendar + Google Calendar (conflict detection)
│   ├── whatsapp/               # follow-up interface (noop + Cloud API stub)
│   ├── db/                     # async SQLAlchemy models + repositories
│   ├── analytics/              # Prometheus metrics + latency tracker
│   └── api/                    # FastAPI control plane (health/metrics/outbound)
├── scripts/                    # setup_sip, init_db, benchmarks, outbound
├── migrations/                 # Alembic (async)
├── deploy/                     # nginx, systemd, DigitalOcean setup
├── tests/                      # pytest (state, completion, knowledge, factories)
├── Dockerfile / docker-compose.yml / Makefile
└── ARCHITECTURE.md / DEPLOYMENT.md
```

## Local development

Prereqs: Python 3.11+, Docker (for Postgres), and API keys for LiveKit, Deepgram,
OpenAI, Cartesia.

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env         # fill in credentials

# 3. Database
make dev-db                  # start local Postgres in Docker
make init-db                 # create tables (or: make migrate)

# 4. Provision Vobiz SIP (once) — copy printed IDs into .env
make setup-sip

# 5. Run (two terminals)
make run-agent               # LiveKit worker (dev mode)
make run-api                 # FastAPI control plane
```

Trigger a test outbound call:

```bash
curl -X POST http://localhost:8080/calls/outbound \
  -H "Authorization: Bearer $API_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"+9198XXXXXXXX","lead_name":"Rahul"}'
```

## Benchmarks

```bash
make bench-llm     # GPT-4o-mini TTFT (target < 500 ms)
make bench-tts     # Cartesia TTFB (target < 300 ms)
make bench-e2e     # estimated end-to-end (target < 1000 ms)
python scripts/benchmark_stt.py --audio sample_hindi.wav   # Deepgram (< 300 ms)
```

Live latency is also exported at `/metrics` (`priya_*_latency_seconds`).

## Testing

```bash
make test          # pytest
make lint          # ruff + mypy
```

The tests cover the state machine, lead scoring, summary formatting, knowledge
retrieval and adapter factories — all without network access.

## Docker

```bash
docker compose up -d --build   # postgres + migrate + agent + api
docker compose logs -f agent api
```

## Phase 2 (interfaces only)

CRM, WhatsApp, analytics dashboards, and RAG/vector DB are wired as clean
adapters/factories selected by env vars (`CRM_PROVIDER`, `WHATSAPP_PROVIDER`,
`RAG_PROVIDER`). Phase 1 defaults (`noop`, `markdown`, DB calendar) work out of
the box; enabling a real provider requires only implementing its stub and
flipping the env var — no changes to agent code. See `ARCHITECTURE.md`.

## Security

- All secrets via environment variables; nothing hardcoded.
- Input validation (Pydantic) on the outbound API; E.164 phone validation.
- Bearer-token auth + in-memory rate limiting on the outbound endpoint.
- `/metrics` restricted by nginx to the monitoring network.
- Non-root Docker user; systemd hardening flags.
