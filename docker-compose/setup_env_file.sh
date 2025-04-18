#!/bin/bash

# Check if a path argument is provided
if [ -z "$1" ]; then
    echo "Usage: $0 /path/to/save/.env"
    exit 1
fi

# Use the provided argument as the path for the .env file
ENV_FILE="$1"

# Prompt the user for each variable with default values
read -p "Enter the GENAI_ENGINE_VERSION (default: latest): " GENAI_ENGINE_VERSION
GENAI_ENGINE_VERSION=${GENAI_ENGINE_VERSION:-latest}

read -p "Enter the ML_ENGINE_VERSION (default: latest): " ML_ENGINE_VERSION
ML_ENGINE_VERSION=${ML_ENGINE_VERSION:-latest}

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

read -p "Enter the ARTHUR_API_HOST (default: https://platform.arthur.ai): " ARTHUR_API_HOST
ARTHUR_API_HOST=${ARTHUR_API_HOST:-https://platform.arthur.ai}

read -p "Enter the ARTHUR_CLIENT_ID (default: some_client_id): " ARTHUR_CLIENT_ID
ARTHUR_CLIENT_ID=${ARTHUR_CLIENT_ID:-some_client_id}

read -p "Enter the ARTHUR_CLIENT_SECRET (default: some_client_secret): " ARTHUR_CLIENT_SECRET
ARTHUR_CLIENT_SECRET=${ARTHUR_CLIENT_SECRET:-some_client_secret}

# Create the .env file with the provided values
cat <<EOF > "$ENV_FILE"
GENAI_ENGINE_VERSION=$GENAI_ENGINE_VERSION
ML_ENGINE_VERSION=$ML_ENGINE_VERSION
GENAI_ENGINE_INGRESS_URI=$GENAI_ENGINE_INGRESS_URI
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
APP_SECRET_KEY=$APP_SECRET_KEY
GENAI_ENGINE_OPENAI_PROVIDER=$GENAI_ENGINE_OPENAI_PROVIDER
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS
GENAI_ENGINE_ADMIN_KEY=$GENAI_ENGINE_ADMIN_KEY
ARTHUR_API_HOST=$ARTHUR_API_HOST
ARTHUR_CLIENT_ID=$ARTHUR_CLIENT_ID
ARTHUR_CLIENT_SECRET=$ARTHUR_CLIENT_SECRET
EOF

echo ".env file created at $ENV_FILE"
