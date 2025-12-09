# Model Upload Task - Multi-stage build
# Stage 1: Download models from Hugging Face
# Stage 2: Upload models to S3 (ECS Task)

# =============================================================================
# Stage 1: Download models
# =============================================================================
FROM python:3.13-slim AS downloader

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies (only main dependencies needed for download)
RUN poetry install --no-interaction --no-ansi --only main --no-root

# Copy download script
COPY download_models.py .

# Download all models during build (includes relevance models and PII v2)
RUN poetry run python download_models.py --output-dir /models --workers 4

# =============================================================================
# Stage 2: Upload task
# =============================================================================
FROM python:3.13-slim AS task

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install only runtime dependencies needed for S3 upload
RUN poetry install --no-interaction --no-ansi --only main --no-root

# Copy upload script
COPY upload_models.py .

# Copy downloaded models from stage 1
COPY --from=downloader /models /models

# Environment variables (S3_BUCKET must be provided at runtime)
ENV MODELS_DIR=/models
ENV LOG_LEVEL=INFO

# Run upload task
CMD ["poetry", "run", "python", "upload_models.py"]
