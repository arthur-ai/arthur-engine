# Model Upload Task - Multi-stage distroless build (GCP / Cloud Run)
# Stage 1: Download models from Hugging Face
# Stage 2: Build dependencies (google-cloud-storage)
# Stage 3: Distroless runtime (minimal attack surface)

# =============================================================================
# Stage 1: Download models
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

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies to virtual environment
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-interaction --no-ansi --only main --no-root

# Copy upload script
COPY upload_models.py .

# =============================================================================
# Stage 3: Runtime (slim has libffi etc. required by cffi/cryptography)
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv/lib/python3.12/site-packages /app/site-packages

# Copy application code
COPY --from=builder /app/upload_models.py .

# Copy downloaded models from stage 1
COPY --from=downloader /models /models

# Set Python path to include our dependencies
ENV PYTHONPATH=/app/site-packages
ENV MODELS_DIR=/model-storage
ENV LOG_LEVEL=INFO

# Create non-root user for Cloud Run
RUN groupadd -r nonroot -g 65532 && useradd -r -u 65532 -g nonroot nonroot \
    && chown -R nonroot:nonroot /app
USER nonroot

# Run upload task
ENTRYPOINT ["python", "upload_models.py"]
