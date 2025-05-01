#!/bin/bash

check_docker_compose() {
  if ! command -v docker-compose &> /dev/null && ! command -v docker compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
  fi
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
    echo "Please review the file and press any key to proceed to Docker Compose up..."
    read -n 1 -s
else
    echo ""
    echo "Enter the provider for OpenAI services (Format: Azure or OpenAI)"
    genai_engine_openai_provider=$(prompt_env_var "GENAI_ENGINE_OPENAI_PROVIDER" "OpenAI" "true")
    echo ""
    echo "Enter the OpenAI GPT model name (Example: gpt-4o-mini-2024-07-18)"
    genai_engine_openai_gpt_name=$(prompt_env_var "GENAI_ENGINE_OPENAI_GPT_NAME" "gpt-4o-mini-2024-07-18")
    echo ""
    echo "Enter the OpenAI GPT endpoint (Format: https://endpoint):"
    echo "If using OpenAI provider, leave this blank unless you are using a proxy or OpenAI compatible service emulator."
    genai_engine_openai_gpt_endpoint=$(prompt_env_var "GENAI_ENGINE_OPENAI_GPT_ENDPOINT" "")
    echo ""
    echo "Enter the OpenAI GPT API key:"
    genai_engine_openai_api_key=$(prompt_env_var "GENAI_ENGINE_OPENAI_GPT_API_KEY" "changeme_api_key")

    all_env_vars="GENAI_ENGINE_INGRESS_URI=http://localhost:3030
$genai_engine_openai_provider
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$genai_engine_openai_gpt_name::$genai_engine_openai_gpt_endpoint::$genai_engine_openai_api_key"

    echo "$all_env_vars" > "$env_file"
fi

sleep 1

curl -s https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/docker-compose/genai-engine/docker-compose.yml | docker compose -f - up
