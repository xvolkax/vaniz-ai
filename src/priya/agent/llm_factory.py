"""Pluggable LLM factory — switch providers via LLM_PROVIDER without code edits.

All three providers are OpenAI-compatible, so they share the LiveKit
`openai.LLM` plugin (chat completions API):

  * openai : api.openai.com (GPT-4o-mini)               [default]
  * azure  : Azure AI Foundry v1 endpoint (.../openai/v1) — key-based auth,
             `model` = your Azure *deployment* name. Region-close = lower TTFT.
  * groq   : api.groq.com/openai/v1 — Llama models on LPU, ultra-low TTFT.

Nothing is removed: set LLM_PROVIDER=openai|azure|groq to switch. Each provider
reads only its own credentials, so all can be configured simultaneously.
"""
from __future__ import annotations

from livekit.plugins import openai

from priya.config import settings
from priya.utils.logging import get_logger

log = get_logger(__name__)


def build_llm() -> openai.LLM:
    provider = settings.llm_provider.lower()

    if provider == "azure":
        if not (settings.azure_openai_endpoint and settings.azure_openai_api_key):
            raise RuntimeError(
                "LLM_PROVIDER=azure requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY."
            )
        model = settings.azure_openai_deployment or settings.openai_model
        log.info("llm.provider.azure", endpoint=settings.azure_openai_endpoint, model=model)
        # NOTE: no temperature/parallel_tool_calls passed — some Azure deployments
        # (e.g. gpt-5 family reasoning models) reject non-default temperature.
        # reasoning_effort="minimal" makes gpt-5 respond near-instantly (voice-critical).
        azure_kwargs: dict = {
            "model": model,
            "api_key": settings.azure_openai_api_key,
            "base_url": settings.azure_openai_endpoint,
        }
        if settings.azure_reasoning_effort:
            azure_kwargs["reasoning_effort"] = settings.azure_reasoning_effort
        return openai.LLM(**azure_kwargs)

    if provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("LLM_PROVIDER=groq requires GROQ_API_KEY.")
        log.info("llm.provider.groq", model=settings.groq_model)
        groq_kwargs: dict = {
            "model": settings.groq_model,
            "api_key": settings.groq_api_key,
            "base_url": settings.groq_base_url,
            "temperature": 0.4,
            "parallel_tool_calls": False,
        }
        if settings.llm_max_tokens > 0:
            groq_kwargs["max_completion_tokens"] = settings.llm_max_tokens
        return openai.LLM(**groq_kwargs)

    if provider == "sarvam":
        if not settings.sarvam_api_key:
            raise RuntimeError("LLM_PROVIDER=sarvam requires SARVAM_API_KEY.")
        log.info("llm.provider.sarvam", model=settings.sarvam_llm_model)
        # OpenAI-compatible endpoint. Minimal kwargs — Sarvam uses its own
        # defaults (verified: tool calling works, TTFT ~340ms). sarvam-105b is
        # the agentic/tool-capable model (sarvam-30b does not emit tool_calls).
        sarvam_kwargs: dict = {
            "model": settings.sarvam_llm_model,
            "api_key": settings.sarvam_api_key,
            "base_url": settings.sarvam_base_url,
        }
        if settings.llm_max_tokens > 0:
            sarvam_kwargs["max_completion_tokens"] = settings.llm_max_tokens
        return openai.LLM(**sarvam_kwargs)

    # default: OpenAI
    log.info("llm.provider.openai", model=settings.openai_model)
    kwargs: dict = {
        "model": settings.openai_model,
        "api_key": settings.openai_api_key,
        "temperature": 0.6,
        "parallel_tool_calls": False,
    }
    if settings.llm_max_tokens > 0:
        kwargs["max_completion_tokens"] = settings.llm_max_tokens
    # Only set base_url when explicitly provided (empty string breaks the SDK).
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return openai.LLM(**kwargs)
