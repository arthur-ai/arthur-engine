#!/bin/bash
YELLOW='\033[1;33m'
NC='\033[0m'

if git diff --cached --name-only | grep -q '^arthur-observability-sdk/src/arthur_observability_sdk/'; then
  if ! git diff --cached --name-only | grep -q '^arthur-observability-sdk/docs/'; then
    echo -e "${YELLOW}⚠️  WARNING: You modified arthur-observability-sdk/src/ — consider updating docs/ (run scripts/update-docs.sh).${NC}"
  fi
fi

exit 0  # never blocks a commit
