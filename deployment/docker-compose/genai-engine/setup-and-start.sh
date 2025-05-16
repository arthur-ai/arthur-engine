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

create_directory_if_not_present() {
  local dir_name=$1
  # creates base directories if they don't exist
  if [[ ! -d "$dir_name" ]]; then
    mkdir -p "$dir_name"
    echo "Created directory: $dir_name"
  fi
}

echo "┌───────────────────────────────────────────────────┐"
echo "│     Welcome to the Arthur GenAI Engine Setup!     │"
echo "└───────────────────────────────────────────────────┘"

check_docker_compose

root_dir="$HOME/.arthur-engine-install"
genai_subdir="$root_dir/genai-engine"
env_file=".env"
create_directory_if_not_present "$genai_subdir"

if [[ -f "$genai_subdir/$env_file" ]]; then
    echo "The $genai_subdir/$env_file file already exists."
    echo "Please review the file and press any key to proceed to Docker Compose up..."
    read -n 1 -s
else
    echo ""
    read -p "Do you have access to OpenAI services? (y/n) [Default: y]: " has_openai
    has_openai=${has_openai:-y}

    if [[ $has_openai =~ ^[Yy]$ ]]; then
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

        all_env_vars="$genai_engine_openai_provider
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$genai_engine_openai_gpt_name::$genai_engine_openai_gpt_endpoint::$genai_engine_openai_api_key"
    else
        echo ""
        echo "Skipping OpenAI configuration..."
        all_env_vars=""
    fi

    echo "$all_env_vars" > "$genai_subdir/$env_file"
fi

sleep 1
cd "$genai_subdir"
curl -s https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/docker-compose/genai-engine/docker-compose.yml | docker compose -f - up -d --pull always
