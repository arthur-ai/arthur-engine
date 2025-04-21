#!/bin/bash

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ENV_FILE="$SCRIPT_DIR/.env"

# Check if the .env file exists and source it
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE"
    source "$ENV_FILE"
else
    echo ".env file not found. Prompting for input."
    $SCRIPT_DIR/setup_env_file.sh "$ENV_FILE"
fi

# Start the Docker Compose services
docker compose -f $SCRIPT_DIR/docker-compose.yml up -d
