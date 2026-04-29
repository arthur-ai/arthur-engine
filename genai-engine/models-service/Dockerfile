# Multi-stage build for models-service.
#
# Layout (mirrors genai-engine/Dockerfile patterns):
#   preinstall   → uv pip install + spaCy en_core_web_lg
#   gpu-install  → reinstall torch with CUDA wheel
#   cpu-install  → no-op (uses preinstall's CPU torch)
#   install      → copies src/ — no model weights
#   runtime      → distroless final image
#
# Build args:
#   TORCH_DEVICE=cpu (default) | gpu
#
# Model weights are NOT baked into the image. The server downloads them
# into MODEL_STORAGE_PATH (default /models) at startup, matching the
# genai-engine pattern. Mount a host volume at /models in the compose file
# to persist weights across container restarts.

ARG TORCH_DEVICE=cpu


# ---------------------------------------------------------------------------
# Stage 1 — preinstall: Python deps + spaCy model
# ---------------------------------------------------------------------------
FROM python:3.12.8-slim-bookworm AS preinstall

# uv for dep resolution; lsof + curl for the healthcheck (matches genai-engine).
RUN pip3 install --no-cache-dir uv==0.11.7 \
 && apt-get update \
 && apt-get install -y --no-install-recommends lsof curl \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock /app/
RUN uv export --frozen \
    --no-group dev --no-group linters \
    --no-emit-project \
    -o /tmp/requirements.txt \
 && uv pip install --system --no-cache \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    --index-strategy unsafe-best-match \
    -r /tmp/requirements.txt


# ---------------------------------------------------------------------------
# Stage 2a — gpu-install: replace CPU torch with CUDA wheel
# ---------------------------------------------------------------------------
FROM preinstall AS gpu-install
COPY requirements-gpu.txt /tmp/requirements-torch.txt
RUN uv pip install --system --no-cache --reinstall -r /tmp/requirements-torch.txt


# ---------------------------------------------------------------------------
# Stage 2b — cpu-install: no-op
# ---------------------------------------------------------------------------
FROM preinstall AS cpu-install


# ---------------------------------------------------------------------------
# Stage 3 — install: copy app code, finalize layout
# ---------------------------------------------------------------------------
FROM ${TORCH_DEVICE}-install AS install

COPY src /app/src
COPY scripts /app/scripts

# Empty model directory; weights stream in at runtime via downloader.
RUN mkdir -p /models /home/nonroot \
 && chown -R 65532:65532 /app /models /home/nonroot


# ---------------------------------------------------------------------------
# Stage 4 — runtime: distroless final
# ---------------------------------------------------------------------------
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime

COPY --from=install /usr/lib /usr/lib
COPY --from=install /usr/local/lib/ /usr/local/lib/
COPY --from=install /usr/local/bin/ /usr/local/bin/
COPY --from=install /usr/bin/lsof /usr/bin/lsof
COPY --from=install /usr/bin/curl /usr/bin/curl
COPY --from=install /etc/ld.so.cache /etc/ld.so.cache
COPY --from=install --chown=nonroot:nonroot /app /app
COPY --from=install --chown=nonroot:nonroot /models /models

ENV PATH="/usr/local/bin:/usr/local/sbin:/usr/bin:/sbin:/bin:$PATH" \
    PYTHONPATH="/app/src" \
    UV_SYSTEM_PYTHON=1 \
    MODEL_STORAGE_PATH="/models" \
    MODELS_SERVICE_PORT=7600 \
    MODELS_SERVICE_HOST=0.0.0.0
# HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE intentionally NOT set: the server
# downloads weights at startup. For air-gapped deployments, pre-populate the
# /models volume out-of-band and override the env via compose.

WORKDIR /app

EXPOSE 7600

ENTRYPOINT ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "7600"]
