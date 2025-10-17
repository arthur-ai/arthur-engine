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

parse_boolean() {
  # parse bool from command line to expected python formatting (all lowercase)
  # takes in the name of the command line flag and the value of the flag
  local flag_name=$1
  local value=$(echo "$2" | tr '[:upper:]' '[:lower:]')
  if [[ "$value" != "true" && "$value" != "false" ]]; then
    echo "Usage: $flag_name flag must be set to 'true' or 'false'."
    exit 1
  else
    echo "$value"
  fi
}

parse_script_vars() {
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
        FETCH_RAW_DATA_ENABLED=$(parse_boolean "--fetch-raw-data-enabled" "${1#*=}")
        shift
        ;;
      --default-genai-config=*)
        DEFAULT_GENAI_CONFIG=$(parse_boolean "--default-genai-config" "${1#*=}")
        shift
        ;;
      *)
        echo "Unknown parameter: $1"
        echo "Usage: $0 [--arthur-api-host=HOST] [--arthur-client-id=ID] [--arthur-client-secret=SECRET] [--fetch-raw-data-enabled=BOOL] [--default-genai-config=BOOL]"
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
  local required_vars=("ARTHUR_CLIENT_ID" "ARTHUR_CLIENT_SECRET")
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

echo "┌─────────────────────────────────────────────┐"
echo "│     Welcome to the Arthur Engine Setup!     │"
echo "└─────────────────────────────────────────────┘"

check_docker_compose

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

# parse command line arguments - will overwrite any existing .env variables
parse_script_vars "$@"

# validate required ML engine variables
if missing_ml_engine_vars; then
  echo "The following format is required to set ML engine variables."
  echo "Usage: $0 [--arthur-api-host=HOST] [--arthur-client-id=ID] [--arthur-client-secret=SECRET] [--fetch-raw-data-enabled=BOOL] [--default-genai-config=BOOL]"
  exit 1
fi

# set default env vars for ml-engine if unset in both existing .env and command line
ARTHUR_API_HOST=${ARTHUR_API_HOST:-"https://platform.arthur.ai"}
FETCH_RAW_DATA_ENABLED=${FETCH_RAW_DATA_ENABLED:-"true"}
DEFAULT_GENAI_CONFIG=${DEFAULT_GENAI_CONFIG:-"false"}

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

# handle OpenAI configuration for GenAI engine
if [[ "$DEFAULT_GENAI_CONFIG" == "true" ]]; then
    # skip OpenAI configuration entirely when default flag is set
    echo ""
    echo "Skipping OpenAI configuration as --default-genai-config is set..."
    # make sure we preserve existing open AI configs if they're already in the .env file
    if [[ ! -z $GENAI_ENGINE_OPENAI_PROVIDER  ]]; then
      all_env_vars+="GENAI_ENGINE_OPENAI_PROVIDER=$GENAI_ENGINE_OPENAI_PROVIDER"
    fi
    if [[ ! -z $GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS  ]]; then
      all_env_vars+="
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS"
    fi
else
    if [[ -z "$GENAI_ENGINE_OPENAI_PROVIDER" ]]; then
        # run prompts for OpenAI configuration if it's not already set in .env
        echo ""
        echo "Do you have access to OpenAI services?"
        echo ""
        echo "Why we ask: Arthur uses your OpenAI key to run guardrails like hallucination and sensitive data checks—all within your environment, so your data never leaves your infrastructure."
        echo "You can use a new or existing key tied to the OpenAI project/org your LLM calls are billed to."
        echo "Don't have a key? You can skip for now and add it later. Just note: hallucination & sensitive data guardrails won't run without it."
        echo ""
        read -p "Do you have access to OpenAI? (y/n) [Default: y]: " has_openai
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
        echo ""
        echo "Skipping OpenAI Configuration because it is already set in the config file..."
        # use existing OpenAI configuration from .env
        all_env_vars+="GENAI_ENGINE_OPENAI_PROVIDER=$GENAI_ENGINE_OPENAI_PROVIDER
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS"
    fi
fi

# Prompt for secret store key if not already set
if [[ -z "$GENAI_ENGINE_SECRET_STORE_KEY" ]]; then
    echo ""
    echo "Enter the secret store encryption key for securing sensitive data:"
    echo "This key is used to encrypt/decrypt secrets stored in the database."
    echo "Keep this key secure and consistent across deployments."
    echo "(Leave empty to auto-generate a secure random key)"
    read -p "GENAI_ENGINE_SECRET_STORE_KEY: " genai_engine_secret_store_key

    if [[ -z "$genai_engine_secret_store_key" ]]; then
        # Generate a secure random key using /dev/urandom
        genai_engine_secret_store_key=$(LC_ALL=C tr -dc 'A-Za-z0-9!"#$%&'\''()*+,-./:;<=>?@[\]^_`{|}~' </dev/urandom | head -c 32)
        echo "Generated random secret key: $genai_engine_secret_store_key"
        echo "This key is stored in the .env file and will be used to encrypt/decrypt secrets stored in the database."
        echo "Please save this key securely for future deployments!"
    fi

    all_env_vars+="
GENAI_ENGINE_SECRET_STORE_KEY=$genai_engine_secret_store_key"
else
    echo ""
    echo "Using existing GENAI_ENGINE_SECRET_STORE_KEY from config file..."
    all_env_vars+="
GENAI_ENGINE_SECRET_STORE_KEY=$GENAI_ENGINE_SECRET_STORE_KEY"
fi

echo "$all_env_vars" > "$engine_subdir/$env_file"
echo ""
echo "Updated $env_file file at $engine_subdir/$env_file"
echo ""
echo "To see the $env_file file or docker-compose.yml, look in the $engine_subdir directory."
echo "We discourage moving this directory so you can continue using our automated workflow to update your configuration."
echo ""
echo "Downloading images (~2.86 GB) and running docker containers. This will take a few minutes..."
echo ""

sleep 1
cd "$engine_subdir"
curl -s https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/docker-compose/arthur-engine/docker-compose.yml > "docker-compose.yml"
docker compose up -d --pull always
