#!/bin/bash

set -e

cd "$(dirname "$0")/.."

uv sync --project python --group dev -q
uv run --project python black src/arthur_observability_sdk tests
uv run --project python autoflake --remove-all-unused-imports --in-place --recursive --quiet src/arthur_observability_sdk tests
uv run --project python isort src/arthur_observability_sdk tests --profile black
uv run --project python mypy src/arthur_observability_sdk

YELLOW='\033[1;33m'
NC='\033[0m'
if git diff --name-only HEAD -- python/src/arthur_observability_sdk/ 2>/dev/null | grep -q .; then
  if ! git diff --name-only HEAD -- docs/ 2>/dev/null | grep -q .; then
    echo -e "${YELLOW}⚠️  WARNING: python/src/arthur_observability_sdk/ has changes but docs/ does not. Consider running scripts/update-docs.sh.${NC}"
  fi
fi
