#!/bin/bash

set -e

docker compose up -d db

export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=changeme_pg_password
export POSTGRES_URL=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=arthur_genai_engine
export POSTGRES_USE_SSL=false
export GENAI_ENGINE_ENABLE_PERSISTENCE=enabled

export GENAI_ENGINE_ENVIRONMENT=local
export GENAI_ENGINE_ADMIN_KEY=changeme123
export GENAI_ENGINE_INGRESS_URI=http://localhost:3030
export ALLOW_ADMIN_KEY_GENERAL_ACCESS=enabled

export GENAI_ENGINE_OPENAI_PROVIDER=Azure
export OPENAI_API_VERSION=2023-07-01-preview
export GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=model_name::https://my_service.openai.azure.com/::my_api_key
export PYTHONPATH="src:$PYTHONPATH"

export GENAI_ENGINE_SECRET_STORE_KEY=changeme_secret_store_key

poetry run alembic upgrade head

poetry run gunicorn src.server:get_app -c src/gunicorn.conf.py --reload
