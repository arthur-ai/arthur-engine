# Model Upload - Multi-stage build with three named runtime targets
#
# Build args:
#   BACKEND: s3 (ECS) | gcs (GCP) | fs (K8s PVC / EFS / any mounted volume)  [default: s3]
#
# Build commands:
#   docker build --build-arg BACKEND=s3  --target runtime-s3  -t <image> .
#   docker build --build-arg BACKEND=gcs --target runtime-gcs -t <image> .
#   docker build --build-arg BACKEND=fs  --target runtime-fs  -t <image> .
#
# Runtime is Python 3.12 (per requires-python) on Debian bookworm. The distroless
# runtimes (s3, fs) copy the apt-upgraded Python 3.12 runtime + patched system
# libraries from the builder stage over the distroless base (whose own python3 is
# the unused, vulnerable 3.11, which is removed). Images are linux/amd64 only.

ARG BACKEND=s3

# =============================================================================
# Stage 1: Download models (shared across all backends)
# =============================================================================
FROM python:3.12-slim-bookworm AS downloader
ARG BACKEND

WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.7
COPY pyproject.toml uv.lock* ./

RUN uv export --frozen --no-emit-project --no-hashes -o /tmp/requirements.txt \
    && uv pip install --system --no-cache -r /tmp/requirements.txt

COPY download_models.py .

RUN python download_models.py --output-dir /models --workers 4

# =============================================================================
# Stage 2: Install backend-specific runtime deps + apply Debian security fixes
#   - s3:  boto3
#   - gcs: google-cloud-storage
#   - fs:  nothing (stdlib only)
#
# `apt-get upgrade` patches base-image OS CVEs (libssl3, libc6, ...). The upgraded
# shared objects in /usr/lib and the Python 3.12 runtime in /usr/local are copied
# into the distroless runtime images below, so the binaries that actually ship
# contain the fixes (the distroless base's dpkg metadata, which scanners read,
# stays stale — see security/vex/openvex.json).
# =============================================================================
FROM python:3.12-slim-bookworm AS builder
ARG BACKEND

RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.7
COPY pyproject.toml uv.lock* ./

RUN if [ "$BACKEND" != "fs" ]; then \
      uv export --frozen --no-emit-project --no-hashes --extra "$BACKEND" \
        -o /tmp/requirements.txt \
      && pip install --target=/app/site-packages --no-cache \
           -r /tmp/requirements.txt; \
    fi

# =============================================================================
# Runtime: ECS / S3  (distroless)
# =============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime-s3

# Bring the apt-upgraded Python 3.12 runtime and patched system libraries from the
# builder over the distroless base (whose own python3 is the unused, vulnerable 3.11).
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/lib /usr/lib
COPY --from=builder /etc/ld.so.cache /etc/ld.so.cache

# Remove the unused Python 3.11 runtime inherited from the distroless base so it
# neither ships nor trips scanners (CVE-2025-8194, CVE-2025-13836). The job runs on
# Python 3.12 from /usr/local. distroless has no shell, so use exec-form rm with
# explicit amd64 paths (these images are linux/amd64 only); rm deletes itself last.
USER root
COPY --from=builder /usr/bin/rm /usr/bin/rm
RUN ["/usr/bin/rm", "-rf", \
     "/usr/lib/python3.11", \
     "/usr/bin/python3.11", \
     "/usr/lib/x86_64-linux-gnu/libpython3.11.so.1.0", \
     "/var/lib/dpkg/status.d/python3.11-minimal", \
     "/var/lib/dpkg/status.d/libpython3.11-minimal", \
     "/var/lib/dpkg/status.d/libpython3.11-stdlib", \
     "/usr/bin/rm"]
USER nonroot

WORKDIR /app
COPY --from=builder /app/site-packages /app/site-packages
COPY --from=downloader /models /models
COPY --chown=nonroot:nonroot upload_models.py /app/

ENV BACKEND=s3 \
    PATH="/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin" \
    PYTHONPATH=/app/site-packages \
    MODELS_DIR=/models \
    LOG_LEVEL=INFO

ENTRYPOINT ["python", "/app/upload_models.py"]

# =============================================================================
# Runtime: Filesystem / FS  (distroless — no extra deps, stdlib only)
# Covers any mounted volume: K8s PVC, AWS EFS, OpenShift, etc.
# Set TARGET_DIR to the mount path at runtime (default: /models-output)
# =============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime-fs

# Bring the apt-upgraded Python 3.12 runtime and patched system libraries from the
# builder over the distroless base (whose own python3 is the unused, vulnerable 3.11).
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/lib /usr/lib
COPY --from=builder /etc/ld.so.cache /etc/ld.so.cache

# Remove the unused Python 3.11 runtime inherited from the distroless base (see s3 stage).
USER root
COPY --from=builder /usr/bin/rm /usr/bin/rm
RUN ["/usr/bin/rm", "-rf", \
     "/usr/lib/python3.11", \
     "/usr/bin/python3.11", \
     "/usr/lib/x86_64-linux-gnu/libpython3.11.so.1.0", \
     "/var/lib/dpkg/status.d/python3.11-minimal", \
     "/var/lib/dpkg/status.d/libpython3.11-minimal", \
     "/var/lib/dpkg/status.d/libpython3.11-stdlib", \
     "/usr/bin/rm"]
USER nonroot

WORKDIR /app
COPY --from=downloader /models /models
COPY --chown=nonroot:nonroot upload_models.py /app/

ENV BACKEND=fs \
    PATH="/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin" \
    MODELS_DIR=/models \
    TARGET_DIR=/models-output \
    LOG_LEVEL=INFO

ENTRYPOINT ["python", "/app/upload_models.py"]

# =============================================================================
# Runtime: GCP / GCS  (slim — google-auth requires libffi)
# apt-get upgrade patches base OS CVEs here directly (the slim image's dpkg
# metadata is updated too, so scanners see the fixed versions).
# =============================================================================
FROM python:3.12-slim-bookworm AS runtime-gcs

RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*
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
