# Priya — Architecture

## 1. System overview

```
                         ┌───────────────────────────────────────────────┐
                         │                DigitalOcean (blr1/sgp1)         │
                         │                                                 │
   PSTN / Mobile         │   ┌──────────┐        ┌──────────────────────┐ │
  ┌───────────┐  SIP     │   │  LiveKit │  audio │   Agent Worker(s)     │ │
  │  Caller    │◀───────▶│──▶│  (Cloud/ │◀──────▶│  (priya.agent.worker) │ │
  └───────────┘  Vobiz   │   │  self-   │  RTC   │                       │ │
        ▲     virtual №  │   │  hosted) │        │  AgentSession:        │ │
        │                │   └──────────┘        │   Silero VAD          │ │
        │                │        ▲              │   Multilingual Turn   │ │
        │                │        │ dispatch     │     Detector (EOU)    │ │
        │                │        │ rule/API     │   Deepgram Nova-3 STT │ │
        │                │        │              │   GPT-4o-mini  LLM    │ │
        │                │   ┌──────────┐        │   Cartesia Sonic TTS  │ │
        │                │   │ FastAPI  │        │   function tools      │ │
        │                │   │ control  │        └───────────┬───────────┘ │
        │                │   │ plane    │                    │             │
        │                │   │ /healthz │            async writes          │
        │                │   │ /metrics │                    ▼             │
        │                │   │ /calls/  │        ┌──────────────────────┐  │
        │                │   │ outbound │───────▶│     PostgreSQL 16     │  │
        │                │   └────┬─────┘        │ leads/calls/summaries │  │
        │                │        │              │ appointments/audit    │  │
        │                │   ┌────▼─────┐        └──────────────────────┘  │
        │                │   │  nginx   │                                   │
        └────────────────┼──▶│  TLS RP  │   Prometheus scrape → /metrics    │
                         │   └──────────┘                                   │
                         └───────────────────────────────────────────────┘

  Pluggable (Phase 2, behind interfaces): CRM · WhatsApp · Google Calendar · Vector DB
```

Two processes, one image:
- **Agent worker** (`priya.agent.worker`) — joins LiveKit rooms and runs the
  realtime voice pipeline. Scale horizontally for concurrency.
- **API control plane** (`priya.api.main`) — health, metrics, and the
  authenticated outbound-call trigger. Stateless; scale behind nginx.

## 2. Call flow (turn latency budget)

```
user speaks ──▶ Silero VAD detects speech
             ──▶ Deepgram streams interim + final transcript      (~STT < 300ms)
             ──▶ MultilingualModel decides end-of-turn (semantic) (endpointing ~250ms)
             ──▶ GPT-4o-mini streams response (preemptive)        (~LLM TTFT < 500ms)
             ──▶ Cartesia streams first audio byte                (~TTS TTFB < 300ms)
agent speaks ◀── playback begins; caller can barge-in at any time
```

Overlap (preemptive generation begins before turn is fully confirmed) keeps the
perceived end-to-end response under ~1s. Metrics for every stage are recorded to
Prometheus and averaged per call into the `calls` table.

## 3. Conversation state machine

```
GREETING → QUALIFICATION → PROPERTY_REQUIREMENTS → BUDGET_COLLECTION
   │                                                      │
   │ (not interested)                                     ▼
   └──────────────▶ CALL_COMPLETION ◀─ SUMMARY ◀─ APPOINTMENT_BOOKING ◀─ TIMELINE_COLLECTION
```

State is held in `ConversationTracker` (per-call, in `AgentSession.userdata`)
and advanced by function tools as data is collected. `prompts.guidance_for()`
injects a short instruction per state to keep the LLM goal-directed and prevent
re-asking answered questions.

## 4. Data model (PostgreSQL)

```
leads
  id (uuid, pk)             name             phone_number (idx)
  city                      property_type    budget_min / budget_max
  preferred_location        buying_timeline  purpose (self_use|investment)
  loan_required             site_visit_interest   preferred_language
  status (new|qualifying|qualified|unqualified|booked|lost)
  qualification_score       extra (json)     crm_external_id
  created_at / updated_at

calls
  id (uuid, pk)             lead_id (fk→leads)      room_name (idx)
  direction (inbound|outbound)   from_number  to_number
  started_at  ended_at  duration_seconds
  outcome (completed|not_interested|callback_requested|transfer_requested|no_answer|failed|voicemail)
  final_state               user_interruptions
  avg_stt_latency_ms  avg_llm_latency_ms  avg_tts_latency_ms  avg_e2e_latency_ms

conversation_summaries
  id (uuid, pk)   call_id (fk→calls, unique)
  summary   key_requirements   qualification_score
  recommended_next_action   follow_up_recommendation   transcript (json)

appointments
  id (uuid, pk)   lead_id (fk→leads)
  type (site_visit|callback|agent_transfer)
  status (scheduled|confirmed|cancelled|completed)
  scheduled_at  duration_minutes  location  notes  external_calendar_event_id

audit_logs
  id (uuid, pk)  actor  action (idx)  entity_type  entity_id  payload (json)  created_at
```

Migrations are managed by Alembic (async env). `scripts/init_db.py` bootstraps
tables for local development.

## 5. Extensibility (Phase 2 adapters)

| Concern | Interface | Phase 1 default | Phase 2 (stubs ready) | Env switch |
|--------|-----------|-----------------|-----------------------|-----------|
| Knowledge/RAG | `KnowledgeRetriever` | `MarkdownRetriever` | `QdrantRetriever` | `RAG_PROVIDER` |
| CRM | `CRMAdapter` | `NoopCRMAdapter` | Zoho / HubSpot / Salesforce | `CRM_PROVIDER` |
| WhatsApp | `FollowUpService` | `NoopFollowUpService` | Cloud API / Gupshup / Twilio | `WHATSAPP_PROVIDER` |
| Calendar | `CalendarProvider` | `DBCalendarProvider` | `GoogleCalendarProvider` | `GOOGLE_CALENDAR_ENABLED` |

Each concern is selected by a factory (`get_*`) reading an env var, so the agent
code never imports a concrete vendor. Adding a provider = implement the
interface + flip the env var.

**RAG migration path**: markdown files are chunked by heading today. To move to
vectors, implement `QdrantRetriever.search` (embed query → ANN search) and set
`RAG_PROVIDER=qdrant`. No agent changes required.

## 6. Scalability plan

- **Concurrency**: each call ≈ one worker job (CPU-bound on VAD + turn detector).
  Scale by increasing agent replicas (`docker compose` `deploy.replicas`, or a
  systemd template `priya-agent@.service`, or Kubernetes HPA). LiveKit
  distributes jobs across all registered workers with `agent_name=priya-agent`.
- **Right-size**: ~1 vCPU per 3–5 concurrent calls as a starting point; measure
  with `priya_active_calls` and CPU. Prewarm loads Silero VAD once per process.
- **Model files** are baked into the Docker image (`download-files`) so scaling
  out has minimal cold-start.
- **Database**: async pool (size 10 + overflow 20). For high volume, move to a
  managed Postgres (DO Managed DB) and add read replicas for analytics.
- **API**: stateless; run multiple uvicorn workers behind nginx. Replace the
  in-memory rate limiter with Redis for multi-replica correctness.
- **Region**: deploy in `blr1` (Bangalore) or `sgp1` (Singapore) to minimise RTT
  to Indian callers and to STT/LLM/TTS edge PoPs.
- **Backpressure/resilience**: retries (tenacity) on external calls; the audio
  path never blocks on DB or CRM writes; call finalization is idempotent and
  guaranteed via the worker shutdown callback.

## 7. Testing strategy

- **Unit** (fast, no network): state transitions, lead scoring, budget/summary
  formatting, markdown retrieval, adapter factories, API schema validation.
- **Integration** (opt-in): spin up Postgres via `make dev-db`, run repository
  round-trips and `finalize_call` against a real DB.
- **Latency/benchmark**: `scripts/benchmark_*` measure each stage against targets;
  wire into CI as non-blocking informational checks.
- **Live smoke**: `make setup-sip` then place a test call; verify a `calls` row,
  a `conversation_summaries` row, and `/metrics` counters increment.
