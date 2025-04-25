#!/bin/bash

check_docker_compose() {
  if ! command -v docker-compose &> /dev/null && ! command -v docker compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
  fi
}

generate_random_password() {
    # Set the LC_CTYPE to C to handle any byte sequences
    LC_ALL=C < /dev/urandom tr -dc 'A-Za-z0-9!' | head -c 16
}

prompt_env_var() {
  local var_name=$1
  local default_value=$2
  local output_key_pair=$3
  local input_value

  read -p "$var_name [Default: $default_value]: " input_value
  if [[ -z "$input_value" ]]; then
    input_value=$default_value
  fi

  if [[ -n "$output_key_pair" ]]; then
    echo "$var_name=$input_value"
  else
    echo "$input_value"
  fi
}

echo "┌───────────────────────────────────────────────────┐"
echo "│     Welcome to the Arthur GenAI Engine Setup!     │"
echo "└───────────────────────────────────────────────────┘"

check_docker_compose

env_file=".env"
if [[ -f "$env_file" ]]; then
    echo "The .env file already exists."
    echo "Press any key to proceed to Docker Compose up..."
    read -n 1 -s
else
    random_postgres_password=$(generate_random_password)
    postgres_password="POSTGRES_PASSWORD=$random_postgres_password"
    random_app_secret_key=$(generate_random_password)
    app_secret_key="APP_SECRET_KEY=$random_app_secret_key"
    random_genai_engine_admin_key=$(generate_random_password)
    genai_engine_admin_key="GENAI_ENGINE_ADMIN_KEY=$random_genai_engine_admin_key"

    echo "Enter the ingress URL (Format: http(s)://<DNS>)"
    echo "The address of the proxy or the load balancer if you have one"
    genai_engine_ingress_uri=$(prompt_env_var "GENAI_ENGINE_INGRESS_URI" "http://localhost:3030" "true")
    echo ""
    echo "Enter the provider for OpenAI services (Format: Azure or OpenAI)"
    genai_engine_openai_provider=$(prompt_env_var "GENAI_ENGINE_OPENAI_PROVIDER" "OpenAI" "true")
    echo ""
    echo "Enter the OpenAI GPT model name (Example: gpt-4o-mini-2024-07-18)"
    genai_engine_openai_gpt_name=$(prompt_env_var "GENAI_ENGINE_OPENAI_GPT_NAME" "gpt-4o-mini-2024-07-18")
    echo ""
    echo "Enter the OpenAI GPT endpoint (Format: https://endpoint):"
    echo "If using OpenAI provider, leave this blank unless you are using a proxy or service emulator (eg: OpenAI API compatible model)"
    genai_engine_openai_gpt_endpoint=$(prompt_env_var "GENAI_ENGINE_OPENAI_GPT_ENDPOINT" "")
    echo ""
    echo "Enter the OpenAI GPT API key:"
    genai_engine_openai_api_key=$(prompt_env_var "GENAI_ENGINE_OPENAI_GPT_API_KEY" "changeme_api_key")

    all_env_vars="$postgres_password
$app_secret_key
$genai_engine_openai_provider
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$genai_engine_openai_gpt_name::$genai_engine_openai_gpt_endpoint::$genai_engine_openai_api_key
$genai_engine_admin_key"

    echo "$all_env_vars" > "$env_file"
fi

sleep 1

curl -s https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/dev/deployment/docker-compose/genai-engine/docker-compose.yml | docker compose -f - up
