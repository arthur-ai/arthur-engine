# Model Upload - Multi-stage build with three named runtime targets
#
# Build args:
#   BACKEND: s3 (ECS) | gcs (GCP) | pvc (K8s/OpenShift)  [default: s3]
#
# Build commands:
#   docker build --build-arg BACKEND=s3  --target runtime-s3  -t <image> .
#   docker build --build-arg BACKEND=gcs --target runtime-gcs -t <image> .
#   docker build --build-arg BACKEND=pvc --target runtime-pvc -t <image> .

ARG BACKEND=s3

# =============================================================================
# Stage 1: Download models + tiktoken encodings (shared across all backends)
#   All backends include tiktoken to support airgapped deployments.
# =============================================================================
FROM python:3.12-slim AS downloader
ARG BACKEND

WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.7
COPY pyproject.toml uv.lock* ./

RUN uv export --frozen --no-emit-project --extra k8s -o /tmp/requirements.txt \
    && uv pip install --system --no-cache -r /tmp/requirements.txt

COPY download_models.py .

RUN python download_models.py --output-dir /models --workers 4 --include-tiktoken

# =============================================================================
# Stage 2: Install backend-specific runtime deps
#   - s3:  boto3
#   - gcs: google-cloud-storage
#   - pvc: nothing (stdlib only; tiktoken only needed at download time)
# =============================================================================
FROM python:3.12-slim AS builder
ARG BACKEND

WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.7
COPY pyproject.toml uv.lock* ./

RUN if [ "$BACKEND" != "pvc" ]; then \
      uv export --frozen --no-emit-project --extra "$BACKEND" \
        -o /tmp/requirements.txt \
      && pip install --prefix=/app/site-packages --no-cache \
           -r /tmp/requirements.txt; \
    fi

# =============================================================================
# Runtime: ECS / S3  (distroless)
# =============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime-s3

WORKDIR /app
COPY --from=builder /app/site-packages /app/site-packages
COPY --from=downloader /models /models
COPY --chown=nonroot:nonroot upload_models.py /app/

ENV BACKEND=s3 \
    PYTHONPATH=/app/site-packages \
    MODELS_DIR=/models \
    LOG_LEVEL=INFO

USER nonroot
ENTRYPOINT ["python", "/app/upload_models.py"]

# =============================================================================
# Runtime: K8s / PVC  (distroless — no extra deps, stdlib only)
# =============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime-pvc

WORKDIR /app
COPY --from=downloader /models /models
COPY --chown=nonroot:nonroot upload_models.py /app/

ENV BACKEND=pvc \
    MODELS_DIR=/models \
    TARGET_DIR=/models-output \
    LOG_LEVEL=INFO

USER nonroot
ENTRYPOINT ["python", "/app/upload_models.py"]

# =============================================================================
# Runtime: GCP / GCS  (slim — google-auth requires libffi)
# =============================================================================
FROM python:3.12-slim AS runtime-gcs

RUN useradd --uid 65532 --no-create-home nonroot

WORKDIR /app
COPY --from=builder /app/site-packages /app/site-packages
COPY --from=downloader /models /models
COPY upload_models.py /app/

ENV BACKEND=gcs \
    PYTHONPATH=/app/site-packages \
    MODELS_DIR=/models \
    LOG_LEVEL=INFO

USER nonroot
ENTRYPOINT ["python", "/app/upload_models.py"]
