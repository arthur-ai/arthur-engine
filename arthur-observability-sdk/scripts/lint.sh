#!/bin/bash

set -e

cd "$(dirname "$0")/.."

poetry -C python run black src/arthur_observability_sdk tests
poetry -C python run autoflake --remove-all-unused-imports --in-place --recursive --quiet src/arthur_observability_sdk tests
poetry -C python run isort src/arthur_observability_sdk tests --profile black
poetry -C python run mypy src/arthur_observability_sdk

YELLOW='\033[1;33m'
NC='\033[0m'
if git diff --name-only HEAD -- python/src/arthur_observability_sdk/ 2>/dev/null | grep -q .; then
  if ! git diff --name-only HEAD -- docs/ 2>/dev/null | grep -q .; then
    echo -e "${YELLOW}⚠️  WARNING: python/src/arthur_observability_sdk/ has changes but docs/ does not. Consider running scripts/update-docs.sh.${NC}"
  fi
fi
