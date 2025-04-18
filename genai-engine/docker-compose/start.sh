#!/bin/bash

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ENV_FILE="$SCRIPT_DIR/.env"

# Check if the .env file exists and source it
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE"
    source "$ENV_FILE"
else
    echo ".env file not found. Prompting for input."

    # Prompt the user for each variable with default values
    read -p "Enter the GENAI_ENGINE_VERSION (default: latest): " GENAI_ENGINE_VERSION
    GENAI_ENGINE_VERSION=${GENAI_ENGINE_VERSION:-latest}

    read -p "Enter the GENAI_ENGINE_INGRESS_URI (default: http://localhost:3000): " GENAI_ENGINE_INGRESS_URI
    GENAI_ENGINE_INGRESS_URI=${GENAI_ENGINE_INGRESS_URI:-http://localhost:3000}

    read -p "Enter the POSTGRES_PASSWORD (default: changeme_pg_password): " POSTGRES_PASSWORD
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme_pg_password}

    read -p "Enter the APP_SECRET_KEY (default: changeme_app_secret_key): " APP_SECRET_KEY
    APP_SECRET_KEY=${APP_SECRET_KEY:-changeme_app_secret_key}

    read -p "Enter the GENAI_ENGINE_OPENAI_PROVIDER (default: Azure): " GENAI_ENGINE_OPENAI_PROVIDER
    GENAI_ENGINE_OPENAI_PROVIDER=${GENAI_ENGINE_OPENAI_PROVIDER:-Azure}

    read -p "Enter the GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS (default: model_name::https://my_service.openai.azure.com/::my_api_key): " GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS
    GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=${GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS:-model_name::https://my_service.openai.azure.com/::my_api_key}

    read -p "Enter the GENAI_ENGINE_ADMIN_KEY (default: changeme_genai_engine_admin_key): " GENAI_ENGINE_ADMIN_KEY
    GENAI_ENGINE_ADMIN_KEY=${GENAI_ENGINE_ADMIN_KEY:-changeme_genai_engine_admin_key}

    # Create the .env file with the provided values
    cat <<EOF > $ENV_FILE
GENAI_ENGINE_INGRESS_URI=$GENAI_ENGINE_INGRESS_URI
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
APP_SECRET_KEY=$APP_SECRET_KEY
GENAI_ENGINE_OPENAI_PROVIDER=$GENAI_ENGINE_OPENAI_PROVIDER
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS
GENAI_ENGINE_ADMIN_KEY=$GENAI_ENGINE_ADMIN_KEY
EOF
fi

# Run the docker-compose command
curl -s https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/genai-engine/docker-compose/docker-compose.yml | docker-compose -f - up \
