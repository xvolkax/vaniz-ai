# syntax=docker/dockerfile:1

# =========================================================================
# Priya Voice Agent — multi-stage image (agent worker + API share one image)
# =========================================================================
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# System deps: libgomp for onnxruntime (VAD + turn detector), certs, curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- Python dependencies (cached layer) ----
COPY requirements.txt ./
RUN pip install -r requirements.txt

# ---- App source ----
COPY pyproject.toml ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts

# ---- Pre-download ML model files (Silero VAD + multilingual turn detector) ----
# Bakes weights into the image so cold-start latency is minimal in production.
RUN python -m priya.agent.worker download-files || true

# Non-root runtime user
RUN useradd --create-home --uid 10001 priya && chown -R priya:priya /app
USER priya

# Default command runs the LiveKit agent worker. Override in compose for the API.
CMD ["python", "-m", "priya.agent.worker", "start"]
