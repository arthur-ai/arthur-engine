# Build image for Anthropic's OSS Scanner (https://github.com/anthropics/oss-scanner).
# The scanner builds this with the repository as the build context and network access, then runs the
# audit with no network, so every dependency the code and its unit tests need is installed here.
# Mirrors the unit-test jobs in .github/workflows/arthur-engine-workflow.yml.
FROM python:3.12-bookworm

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

# Same uv version as .github/workflows/composite-actions/setup-uv.
RUN curl -LsSf --retry 5 https://astral.sh/uv/0.11.7/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

# scanner contract: the checkout lives inside the image, at /src
COPY . /src
WORKDIR /src

# One environment per uv project, from the committed lockfiles. ml-engine pins Python 3.13, which uv
# downloads here while the network is up.
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --directory genai-engine \
    && uv sync --frozen --directory ml-engine \
    && uv sync --frozen --directory arthur-observability-sdk/python

# ml-engine and the SDK import clients generated from the GenAI Engine OpenAPI spec, as their CI
# jobs and arthur-observability-sdk/scripts/generate_openapi_client.sh do.
RUN pip install --no-cache-dir 'openapi-generator-cli[jdk4py]==7.12' \
    && openapi-generator-cli generate -g python \
      -i genai-engine/staging.openapi.json \
      -o ml-engine/src/genai_client \
      --skip-validate-spec --package-name genai_client \
    && openapi-generator-cli generate -g python \
      -i genai-engine/staging.openapi.json \
      -o /tmp/arthur_genai_client_build \
      --skip-validate-spec --package-name arthur_genai_client \
    && cp -r /tmp/arthur_genai_client_build/arthur_genai_client arthur-observability-sdk/python/src/ \
    && rm -rf /tmp/arthur_genai_client_build

# genai-engine counts tokens with tiktoken, which downloads its encodings on first use.
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken
RUN uv run --no-sync --directory genai-engine python -c \
      "import tiktoken; [tiktoken.get_encoding(e) for e in ('cl100k_base', 'o200k_base')]"

# Offline from here on. The guardrail scorers download Hugging Face models on first use; tests that
# need them fail without a network, and the threat model says so.
ENV UV_OFFLINE=1 \
    HF_HUB_OFFLINE=1 \
    GENAI_ENGINE_SECRET_STORE_KEY=changeme_secret_store_key

# Cheap check that the image works; a failure here does not fail the build.
RUN (uv run --no-sync --directory ml-engine pytest tests/unit -q -x -p no:cacheprovider \
      || echo "WARNING: ml-engine unit tests reported failures")
