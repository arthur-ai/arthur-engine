# Model Upload Task - Unified multi-backend Dockerfile
# Supports S3 (AWS), GCS (Google Cloud), and Filesystem (Kubernetes PVC)
#
# Build with --build-arg BACKEND=<s3|gcs|k8s> to select the backend
#
# Examples:
#   docker build --build-arg BACKEND=s3 -t arthurplatform/genai-engine-models:latest-s3 .
#   docker build --build-arg BACKEND=gcs -t arthurplatform/genai-engine-models:latest-gcs .
#   docker build --build-arg BACKEND=k8s -t arthurplatform/genai-engine-models:latest-k8s .

# =============================================================================
# Stage 1: Download models from Hugging Face
# =============================================================================
FROM python:3.12-slim AS downloader

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies (only main dependencies needed for download)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main --no-root

# Copy download script
COPY download_models.py .

# Download all models during build (includes relevance models and PII v2)
RUN python download_models.py --output-dir /models --workers 4

# =============================================================================
# Stage 2: Build dependencies for runtime
# =============================================================================
FROM python:3.12-slim AS builder

# Backend selection (s3, gcs, or k8s)
ARG BACKEND=s3
ENV BACKEND=${BACKEND}

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies based on backend
# - s3: Install boto3
# - gcs: Install google-cloud-storage
# - k8s: Install nothing (uses stdlib only)
RUN poetry config virtualenvs.in-project true && \
    if [ "$BACKEND" = "s3" ]; then \
        echo "Installing S3 dependencies..." && \
        poetry install --no-interaction --no-ansi --only main --no-root --extras s3; \
    elif [ "$BACKEND" = "gcs" ]; then \
        echo "Installing GCS dependencies..." && \
        poetry install --no-interaction --no-ansi --only main --no-root --extras gcs; \
    elif [ "$BACKEND" = "k8s" ]; then \
        echo "Installing base dependencies (no cloud provider deps)..." && \
        poetry install --no-interaction --no-ansi --only main --no-root; \
    else \
        echo "ERROR: Invalid BACKEND=${BACKEND}. Must be s3, gcs, or k8s" && exit 1; \
    fi

# Copy upload script
COPY upload_models.py .

# =============================================================================
# Stage 3: Runtime
# =============================================================================
# For GCS: Use slim runtime (required for google-cloud-storage's cffi/cryptography)
# For S3/K8s: Use distroless runtime (more secure, smaller attack surface)
#
# To use distroless for S3/K8s, build with --target=runtime-distroless
# To use slim for GCS, build with --target=runtime-slim (default)

# Slim runtime (for GCS)
FROM python:3.12-slim AS runtime-slim

ARG BACKEND=gcs

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv/lib/python3.12/site-packages /app/site-packages

# Copy application code
COPY --from=builder /app/upload_models.py .

# Copy downloaded models from stage 1
COPY --from=downloader /models /models

# Set Python path to include our dependencies
ENV PYTHONPATH=/app/site-packages
ENV MODELS_DIR=/models
ENV LOG_LEVEL=INFO
ENV STORAGE_BACKEND=${BACKEND}

# Create non-root user
RUN groupadd -r nonroot -g 65532 && useradd -r -u 65532 -g nonroot nonroot \
    && chown -R nonroot:nonroot /app
USER nonroot

# Metadata
LABEL org.opencontainers.image.title="Arthur GenAI Engine Models - ${BACKEND}"
LABEL org.opencontainers.image.description="Model upload task for ${BACKEND} backend"
LABEL org.opencontainers.image.vendor="Arthur AI"
LABEL backend="${BACKEND}"

# Run upload task
ENTRYPOINT ["python", "upload_models.py"]

# Distroless runtime (for S3/K8s - more secure)
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime-distroless

ARG BACKEND=s3

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv/lib/python3.12/site-packages /app/site-packages

# Copy application code
COPY --from=builder /app/upload_models.py .

# Copy downloaded models from stage 1
COPY --from=downloader /models /models

# Set Python path to include our dependencies
ENV PYTHONPATH=/app/site-packages
ENV MODELS_DIR=/models
ENV LOG_LEVEL=INFO
ENV STORAGE_BACKEND=${BACKEND}

# Run as non-root user (distroless nonroot image runs as uid 65532)
USER nonroot

# Metadata
LABEL org.opencontainers.image.title="Arthur GenAI Engine Models - ${BACKEND}"
LABEL org.opencontainers.image.description="Model upload task for ${BACKEND} backend"
LABEL org.opencontainers.image.vendor="Arthur AI"
LABEL backend="${BACKEND}"

# Run upload task directly with Python (no shell in distroless)
ENTRYPOINT ["python", "upload_models.py"]
