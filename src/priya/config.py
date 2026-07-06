"""Centralised, validated application configuration.

All configuration is sourced from environment variables (12-factor). No secret
is ever hardcoded. Pydantic performs validation & type coercion at import time.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- App ----------
    app_env: Literal["development", "production"] = "production"
    log_level: str = "INFO"
    service_region: str = "blr1"

    # ---------- LiveKit ----------
    livekit_url: str = Field(default="", alias="LIVEKIT_URL")
    livekit_api_key: str = Field(default="", alias="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(default="", alias="LIVEKIT_API_SECRET")
    agent_name: str = Field(default="priya-agent", alias="AGENT_NAME")

    # ---------- Deepgram ----------
    deepgram_api_key: str = Field(default="", alias="DEEPGRAM_API_KEY")
    deepgram_model: str = Field(default="nova-3", alias="DEEPGRAM_MODEL")
    deepgram_language: str = Field(default="multi", alias="DEEPGRAM_LANGUAGE")

    # ---------- STT provider selection ----------
    # deepgram (default) | sarvam
    stt_provider: str = Field(default="deepgram", alias="STT_PROVIDER")
    sarvam_stt_model: str = Field(default="saarika:v2.5", alias="SARVAM_STT_MODEL")
    sarvam_stt_language: str = Field(default="hi-IN", alias="SARVAM_STT_LANGUAGE")
    # saaras:v3 only — transcribe | translate | verbatim | translit | codemix
    sarvam_stt_mode: str = Field(default="transcribe", alias="SARVAM_STT_MODE")

    # ---------- LLM provider selection ----------
    # openai (default) | azure | groq  — switch without removing any config.
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")

    # ---------- OpenAI ----------
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    # Optional: point to a region-close OpenAI-compatible endpoint (e.g. Azure
    # OpenAI in Central India / Southeast Asia) to cut LLM TTFT for Indian calls.
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")

    # ---------- Azure OpenAI (Foundry v1, OpenAI-compatible) ----------
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field(default="", alias="AZURE_OPENAI_DEPLOYMENT")
    # gpt-5 family reasoning models: "minimal" ~ near-instant (best for voice).
    # Values: minimal | low | medium | high  (blank = let plugin/model decide)
    azure_reasoning_effort: str = Field(default="minimal", alias="AZURE_REASONING_EFFORT")

    # ---------- Groq (OpenAI-compatible, ultra-low latency) ----------
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL"
    )

    # ---------- Sarvam.ai (India-hosted STT/TTS/LLM) ----------
    sarvam_api_key: str = Field(default="", alias="SARVAM_API_KEY")
    # LLM (OpenAI-compatible). sarvam-105b = agentic/tool-capable, Hindi-native.
    sarvam_llm_model: str = Field(default="sarvam-105b", alias="SARVAM_LLM_MODEL")
    sarvam_base_url: str = Field(default="https://api.sarvam.ai/v1", alias="SARVAM_BASE_URL")

    # ---------- Cartesia ----------
    cartesia_api_key: str = Field(default="", alias="CARTESIA_API_KEY")
    cartesia_model: str = Field(default="sonic-3", alias="CARTESIA_MODEL")
    cartesia_voice_id: str = Field(default="", alias="CARTESIA_VOICE_ID")
    cartesia_language: str = Field(default="hi", alias="CARTESIA_LANGUAGE")

    # ---------- Vobiz SIP ----------
    vobiz_sip_host: str = Field(default="", alias="VOBIZ_SIP_HOST")
    vobiz_sip_port: int = Field(default=5060, alias="VOBIZ_SIP_PORT")
    vobiz_sip_username: str = Field(default="", alias="VOBIZ_SIP_USERNAME")
    vobiz_sip_password: str = Field(default="", alias="VOBIZ_SIP_PASSWORD")
    vobiz_phone_number: str = Field(default="", alias="VOBIZ_PHONE_NUMBER")
    sip_inbound_trunk_id: str = Field(default="", alias="SIP_INBOUND_TRUNK_ID")
    sip_outbound_trunk_id: str = Field(default="", alias="SIP_OUTBOUND_TRUNK_ID")
    sip_dispatch_rule_id: str = Field(default="", alias="SIP_DISPATCH_RULE_ID")

    # ---------- Human warm transfer ----------
    # Number of the live sales consultant Priya warm-transfers to. Blank =>
    # transfer disabled (Priya offers a callback instead).
    human_agent_phone: str = Field(default="", alias="HUMAN_AGENT_PHONE")
    # Give up if the human doesn't answer within this many seconds.
    transfer_timeout_seconds: int = Field(default=20, alias="TRANSFER_TIMEOUT_SECONDS")
    # Play hold music to the caller while the human is being dialled.
    transfer_hold_music: bool = Field(default=True, alias="TRANSFER_HOLD_MUSIC")

    # ---------- Database ----------
    database_url: str = Field(
        default="postgresql+asyncpg://priya:priya@localhost:5432/priya",
        alias="DATABASE_URL",
    )

    # ---------- API ----------
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8080, alias="API_PORT")
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")

    # ---------- JWT auth (dashboard / SaaS control-plane) ----------
    # Secret used to sign JWTs. MUST be overridden in production via env.
    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    # Access-token lifetime in minutes (default 12h for dashboard sessions).
    jwt_access_token_expire_minutes: int = Field(
        default=720, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    # Allow public tenant self-signup via POST /auth/register. Disable in prod
    # if tenants are provisioned manually / via billing.
    allow_public_signup: bool = Field(default=True, alias="ALLOW_PUBLIC_SIGNUP")

    # ---------- Campaign execution engine ----------
    # Safety cap on simultaneous outbound calls per campaign (per API replica).
    campaign_max_concurrency: int = Field(default=10, alias="CAMPAIGN_MAX_CONCURRENCY")
    # How often the runner loop wakes to claim work / re-check pause/hours (sec).
    campaign_poll_interval_seconds: float = Field(
        default=5.0, alias="CAMPAIGN_POLL_INTERVAL_SECONDS"
    )
    # Re-launch campaigns left in 'running' state after an API restart.
    campaign_resume_on_startup: bool = Field(default=True, alias="CAMPAIGN_RESUME_ON_STARTUP")

    # ---------- Knowledge source for the agent ----------
    # db (default, SaaS multi-tenant) => properties come from the DB per tenant.
    # yaml (legacy) => single-tenant project.yaml injected once at startup.
    knowledge_source: str = Field(default="db", alias="KNOWLEDGE_SOURCE")
    # Default tenant slug used for inbound calls that can't be resolved to a
    # tenant by dialed number (single-tenant / dev convenience).
    default_tenant_slug: str = Field(default="", alias="DEFAULT_TENANT_SLUG")

    # ---------- Agent context size ----------
    # project = single-builder/single-project prompt with facts injected once
    #           from PROJECT_DATA_PATH; no retrieval at runtime (lowest latency).
    # lite = concise generic prompt + reduced tool set (lower LLM TTFT).
    # full = complete generic prompt + all 9 tools (richer behaviour).
    # ultra = most aggressive trim of the generic prompt.
    agent_context_mode: str = Field(default="project", alias="AGENT_CONTEXT_MODE")

    # Path to the single-project data file (YAML or JSON). Blank => packaged
    # default at src/priya/project/project.yaml. Loaded ONCE at startup.
    project_data_path: str = Field(default="", alias="PROJECT_DATA_PATH")

    # ---------- Turn detection / endpointing ----------
    min_endpointing_delay: float = Field(default=0.4, alias="MIN_ENDPOINTING_DELAY")
    max_endpointing_delay: float = Field(default=2.5, alias="MAX_ENDPOINTING_DELAY")

    # Cap LLM output length. Voice replies should be 1-2 sentences; a hard cap
    # stops runaway responses (seen as multi-second TTS_TOTAL) and trims
    # LLM_TOTAL. 0 = no cap. Not applied to Azure reasoning models.
    llm_max_tokens: int = Field(default=150, alias="LLM_MAX_TOKENS")
    allow_interruptions: bool = Field(default=True, alias="ALLOW_INTERRUPTIONS")
    # livekit = hosted inference.TurnDetector (no local model) | vad | stt
    turn_detection_mode: str = Field(default="livekit", alias="TURN_DETECTION_MODE")
    noise_cancellation_enabled: bool = Field(
        default=False, alias="NOISE_CANCELLATION_ENABLED"
    )

    # ---------- Phase 2 ----------
    crm_provider: str = Field(default="noop", alias="CRM_PROVIDER")
    crm_api_key: str = Field(default="", alias="CRM_API_KEY")
    crm_base_url: str = Field(default="", alias="CRM_BASE_URL")

    whatsapp_provider: str = Field(default="noop", alias="WHATSAPP_PROVIDER")
    whatsapp_api_key: str = Field(default="", alias="WHATSAPP_API_KEY")
    whatsapp_phone_id: str = Field(default="", alias="WHATSAPP_PHONE_ID")

    google_calendar_enabled: bool = Field(default=False, alias="GOOGLE_CALENDAR_ENABLED")
    google_calendar_id: str = Field(default="primary", alias="GOOGLE_CALENDAR_ID")
    google_service_account_json: str = Field(default="", alias="GOOGLE_SERVICE_ACCOUNT_JSON")

    rag_provider: str = Field(default="markdown", alias="RAG_PROVIDER")
    qdrant_url: str = Field(default="", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")

    @computed_field  # type: ignore[misc]
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
