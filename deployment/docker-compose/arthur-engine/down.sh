#!/bin/bash

check_docker_compose() {
  if ! command -v docker-compose &> /dev/null && ! command -v docker compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
  fi
}

check_docker_compose

root_dir="$HOME/.arthur-engine-install"
engine_subdir="$root_dir/arthur-engine"
cd "$engine_subdir"
curl -s https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/docker-compose/arthur-engine/docker-compose.yml | docker compose -f - down
