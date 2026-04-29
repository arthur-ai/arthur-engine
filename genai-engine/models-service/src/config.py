"""Environment-driven configuration for the models service.

All env vars and their defaults live here so callers don't read os.environ directly.
"""

import os

# ---------------------------------------------------------------------------
# Model storage
# ---------------------------------------------------------------------------

# Where baked-in weights live in the runtime image. Loaders look here first
# before falling back to HF Hub model IDs.
MODEL_STORAGE_PATH = os.environ.get("MODEL_STORAGE_PATH", "/models")

# Optional override for an air-gapped or mirrored HF Hub.
# When unset, hf_hub_download uses the public huggingface.co endpoint.
MODEL_REPOSITORY_URL = os.environ.get("MODEL_REPOSITORY_URL")

# Skip all model loading. Useful for tests that don't need real inference.
SKIP_MODEL_LOADING = (
    os.environ.get("MODELS_SERVICE_SKIP_LOADING", "false").lower() == "true"
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

# Bearer token required on every request except /v1/health. Set via .env.shared.
MODEL_REGISTRY_SECRET = os.environ.get("MODEL_REGISTRY_SECRET")


# ---------------------------------------------------------------------------
# Payload limits
# ---------------------------------------------------------------------------

# Single-string text endpoints (prompt_injection, toxicity, pii).
MAX_TEXT_CHARS = 50_000

# claim_filter: bound the array and per-item size separately.
MAX_TEXTS_ITEMS = 500
MAX_TEXT_ITEM_CHARS = 5_000

# Hard ceiling on total request body, enforced via Content-Length middleware.
MAX_REQUEST_BODY_BYTES = 1_000_000


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

PORT = int(os.environ.get("MODELS_SERVICE_PORT", "7600"))
HOST = os.environ.get("MODELS_SERVICE_HOST", "0.0.0.0")
