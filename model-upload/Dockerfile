# Model Upload Task - Unified multi-backend Dockerfile
# Single image supporting S3 (AWS), GCS (Google Cloud), and Filesystem (Kubernetes PVC)
# Backend is selected at runtime via STORAGE_BACKEND env var
#
# Build:
#   docker build -t arthurplatform/genai-engine-models:latest .

# =============================================================================
# Stage 1: Download models from Hugging Face
# =============================================================================
FROM python:3.12-slim AS downloader

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main --no-root

COPY download_models.py .

RUN python download_models.py --output-dir /models --workers 4

# =============================================================================
# Stage 2: Build dependencies for runtime (all backends)
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.in-project true && \
    poetry install --no-interaction --no-ansi --only main --no-root --extras all

COPY upload_models.py .

# =============================================================================
# Stage 3: Runtime (slim — required for google-cloud-storage cffi/cryptography)
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv/lib/python3.12/site-packages /app/site-packages
COPY --from=builder /app/upload_models.py .
COPY --from=downloader /models /models

ENV PYTHONPATH=/app/site-packages
ENV MODELS_DIR=/models
ENV LOG_LEVEL=INFO

RUN groupadd -r nonroot -g 65532 && useradd -r -u 65532 -g nonroot nonroot \
    && chown -R nonroot:nonroot /app
USER nonroot

LABEL org.opencontainers.image.title="Arthur GenAI Engine Models"
LABEL org.opencontainers.image.description="Unified model upload task (S3, GCS, filesystem)"
LABEL org.opencontainers.image.vendor="Arthur AI"

ENTRYPOINT ["python", "upload_models.py"]
