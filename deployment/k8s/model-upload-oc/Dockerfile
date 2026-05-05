# Model Upload Task - Multi-stage distroless build (OpenShift PVC version)
# Stage 1: Download models from Hugging Face
# Stage 2: Build dependencies
# Stage 3: Distroless runtime (minimal attack surface)

# =============================================================================
# Stage 1: Download models
# =============================================================================
FROM python:3.12-slim AS downloader

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv==0.11.7

# Copy project files
COPY pyproject.toml uv.lock* ./

# Install dependencies (only main dependencies needed for download)
RUN uv export --frozen \
    --no-emit-project \
    -o /tmp/requirements.txt \
    && uv pip install --system --no-cache -r /tmp/requirements.txt

# Copy download script
COPY download_models.py .

# Download all models during build (includes relevance models and PII v2)
RUN python download_models.py --output-dir /models --workers 4

# =============================================================================
# Stage 2: Prepare runtime (copy_models.py uses only stdlib, no deps needed)
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Copy copy script (no dependencies needed, uses stdlib only)
COPY copy_models.py .

# =============================================================================
# Stage 3: Distroless runtime
# =============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime

WORKDIR /app

# Copy application code (copy script for PVC, no dependencies needed)
COPY --from=builder --chown=nonroot:nonroot /app/copy_models.py /app/copy_models.py

# Copy downloaded models from stage 1
COPY --chown=nonroot:nonroot --from=downloader /models /models

# Environment variables
ENV MODELS_DIR=/models
ENV LOG_LEVEL=INFO
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run as non-root user (distroless nonroot image runs as uid 65532)
USER nonroot

# Run copy task directly with Python (no shell in distroless)
ENTRYPOINT ["python", "/app/copy_models.py"]
