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

parse_script_vars() {
  # Required ML Engine environment variables
  local required_vars=(
    "ARTHUR_API_HOST"
    "ARTHUR_CLIENT_ID"
    "ARTHUR_CLIENT_SECRET"
    "FETCH_RAW_DATA_ENABLED"
  )

  # Parse command line arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      --arthur-api-host=*)
        ARTHUR_API_HOST="${1#*=}"
        shift
        ;;
      --arthur-client-id=*)
        ARTHUR_CLIENT_ID="${1#*=}"
        shift
        ;;
      --arthur-client-secret=*)
        ARTHUR_CLIENT_SECRET="${1#*=}"
        shift
        ;;
      --fetch-raw-data-enabled=*)
        FETCH_RAW_DATA_ENABLED="${1#*=}"
        shift
        ;;
      *)
        echo "Unknown parameter: $1"
        echo "Usage: $0 [--arthur-api-host=HOST] [--arthur-client-id=ID] [--arthur-client-secret=SECRET] [--fetch-raw-data-enabled=BOOL]"
        exit 1
        ;;
    esac
  done
}

create_directory_if_not_present() {
  local dir_name=$1
  # creates base directories if they don't exist, along with parent directories
  if [[ ! -d "$dir_name" ]]; then
    mkdir -p "$dir_name"
    echo "Created directory: $dir_name"
  fi
}

echo "┌───────────────────────────────────────────────────┐"
echo "│     Welcome to the Arthur GenAI Engine Setup!     │"
echo "└───────────────────────────────────────────────────┘"

check_docker_compose

# parse command line arguments
parse_script_vars "$@"

# create necessary directories if not already present
root_dir="$HOME/.arthur-engine-install"
engine_subdir="$root_dir/arthur-engine"
env_file=".env"
create_directory_if_not_present "$engine_subdir"

if [[ -f "$engine_subdir/$env_file" ]]; then
    echo "The $engine_subdir/$env_file file already exists."
    echo "Please review the file and press any key to proceed to Docker Compose up..."
    echo "Any flags that were set to update environment variables will be ignored."
    read -n 1 -s
else
    # Start with ML engine variables from command line arguments
    if [[ -z "$ARTHUR_API_HOST" || -z "$ARTHUR_CLIENT_ID" || -z "$ARTHUR_CLIENT_SECRET" || -z "$FETCH_RAW_DATA_ENABLED" ]]; then
      echo "The $engine_subdir/$env_file file does not already exist."
      echo "The following format is required when setting up the Arthur engine for the first time."
      echo "Usage: $0 [--arthur-api-host=HOST] [--arthur-client-id=ID] [--arthur-client-secret=SECRET] [--fetch-raw-data-enabled=BOOL]"
      exit 1
    fi
    all_env_vars="########################################################
## Arthur ML Engine Environment Variables
########################################################
ARTHUR_API_HOST=$ARTHUR_API_HOST
ARTHUR_CLIENT_ID=$ARTHUR_CLIENT_ID
ARTHUR_CLIENT_SECRET=$ARTHUR_CLIENT_SECRET
FETCH_RAW_DATA_ENABLED=$FETCH_RAW_DATA_ENABLED

########################################################
## Arthur Gen AI Engine Environment Variables
########################################################
"

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

        all_env_vars+="$genai_engine_openai_provider
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$genai_engine_openai_gpt_name::$genai_engine_openai_gpt_endpoint::$genai_engine_openai_api_key"
    else
        echo ""
        echo "Skipping OpenAI configuration..."
    fi

    echo "$all_env_vars" > "$engine_subdir/$env_file"
    echo "Created combined .env file at $engine_subdir/$env_file"
fi

sleep 1
cd "$engine_subdir"
curl -s https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/docker-compose/arthur-engine/docker-compose.yml | docker compose -f - up -d --pull always
