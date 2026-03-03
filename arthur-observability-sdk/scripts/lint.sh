#!/bin/bash

set -e

cd "$(dirname "$0")/.."

poetry run black src/arthur_observability_sdk tests
poetry run autoflake --remove-all-unused-imports --in-place --recursive --quiet src/arthur_observability_sdk tests
poetry run isort src/arthur_observability_sdk tests --profile black
poetry run mypy src/arthur_observability_sdk

YELLOW='\033[1;33m'
NC='\033[0m'
if git diff --name-only HEAD -- src/arthur_observability_sdk/ 2>/dev/null | grep -q .; then
  if ! git diff --name-only HEAD -- docs/ 2>/dev/null | grep -q .; then
    echo -e "${YELLOW}⚠️  WARNING: src/arthur_observability_sdk/ has changes but docs/ does not. Consider running scripts/update-docs.sh.${NC}"
  fi
fi
