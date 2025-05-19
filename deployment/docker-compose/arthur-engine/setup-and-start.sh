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

read_env_file() {
  local env_file=$1
  if [[ -f "$env_file" ]]; then
    while IFS='=' read -r key value; do
      # skip comments and empty lines
      [[ $key =~ ^#.*$ ]] && continue
      [[ -z $key ]] && continue
      # remove any quotes from the value
      value=$(echo "$value" | tr -d '"'"'")
      # export the variable to env
      export "$key=$value"
    done < "$env_file"
  fi
}

missing_ml_engine_vars() {
  local required_vars=("ARTHUR_API_HOST" "ARTHUR_CLIENT_ID" "ARTHUR_CLIENT_SECRET" "FETCH_RAW_DATA_ENABLED")
  local missing_vars=()

  for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
      missing_vars+=("$var")
    fi
  done

  if [[ ${#missing_vars[@]} -gt 0 ]]; then
    echo "Missing required ML Engine variables:"
    printf '%s\n' "${missing_vars[@]}"
    return 0
  fi

  return 1
}

echo "┌───────────────────────────────────────────────────┐"
echo "│     Welcome to the Arthur GenAI Engine Setup!     │"
echo "└───────────────────────────────────────────────────┘"

check_docker_compose

# parse command line arguments
parse_script_vars "$@"

# create necessary directories if not already present
root_dir="$HOME/.arthur-engine/local-stack"
engine_subdir="$root_dir/arthur-engine"
env_file=".env"
create_directory_if_not_present "$engine_subdir"

# read existing .env file if it exists
if [[ -f "$engine_subdir/$env_file" ]]; then
    echo "Reading existing $engine_subdir/$env_file file..."
    read_env_file "$engine_subdir/$env_file"
fi

# validate required ML engine variables
if missing_ml_engine_vars; then
  echo "The following format is required to set missing required ML engine variables."
  echo "Usage: $0 [--arthur-api-host=HOST] [--arthur-client-id=ID] [--arthur-client-secret=SECRET] [--fetch-raw-data-enabled=BOOL]"
  exit 1
fi

# create or update the .env file
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

# prompt for OpenAI configuration if it's not already set
if [[ -z "$GENAI_ENGINE_OPENAI_PROVIDER" ]]; then
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
else
    # use existing OpenAI configuration
    all_env_vars+="GENAI_ENGINE_OPENAI_PROVIDER=$GENAI_ENGINE_OPENAI_PROVIDER
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS"
fi

echo "$all_env_vars" > "$engine_subdir/$env_file"
echo "Updated $env_file file at $engine_subdir/$env_file"

sleep 1
cd "$engine_subdir"
curl -s https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/docker-compose/arthur-engine/docker-compose.yml > "docker-compose.yml"
docker compose up -d --pull always
