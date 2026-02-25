#!/usr/bin/env bash

set -ex
# don't override if someone already set

# local platform API
export ARTHUR_API_HOST=http://localhost:8000
export ARTHUR_CLIENT_SECRET=7aIHWSEMq2nn474OxZRA_c1T5B0uoXMKz3RO0p1R7ks
export ARTHUR_CLIENT_ID=data-plane-42503663-90eb-46c0-b666-4f962b460942

# setting the data plane with the integration test shield instance
# as if it was a shield instance installed with the data plane

# development genai engine
export GENAI_ENGINE_INTERNAL_API_KEY="LyRW3i4XgxXKD1I31lqR7A58XBOwPNvg"
export GENAI_ENGINE_INTERNAL_HOST=https://engine.development.arthur.ai
export GENAI_ENGINE_INTERNAL_INGRESS_HOST=https://engine.development.arthur.ai

# GCP Gen AI Engine
export GENAI_ENGINE_INTERNAL_API_KEY="LyRW3i4XgxXKD1I31lqR7A58XBOwPNvg"
export GENAI_ENGINE_INTERNAL_HOST=https://136.107.107.225/
export GENAI_ENGINE_INTERNAL_INGRESS_HOST=https://136.107.107.225/

# local genai engine
#export GENAI_ENGINE_INTERNAL_API_KEY="changeme123"
#export GENAI_ENGINE_INTERNAL_HOST=http://localhost:3030
#export GENAI_ENGINE_INTERNAL_INGRESS_HOST=http://localhost:3030


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
(cd "$SCRIPT_DIR/src" && poetry run python ml_engine/job_agent.py)