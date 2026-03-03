#!/usr/bin/env bash
# CI script: diffs PyPI openinference-instrumentation-* packages against pyproject.toml.
# Exits 0 if nothing new, exits 1 with warning if new packages exist on PyPI.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYPROJECT="$SCRIPT_DIR/../pyproject.toml"

echo "Fetching openinference-instrumentation-* packages from PyPI..."
PYPI_PACKAGES=$(curl -s "https://pypi.org/simple/" \
  | grep -oE 'openinference-instrumentation-[a-z0-9-]+' \
  | sed 's/-instrumentation-instrumentation-/-instrumentation-/g' \
  | sort -u \
  | grep -v '^openinference-instrumentation$')

echo "Packages found on PyPI:"
echo "$PYPI_PACKAGES"

echo ""
echo "Packages declared in pyproject.toml:"
DECLARED_PACKAGES=$(grep -oE 'openinference-instrumentation-[a-z0-9-]+' "$PYPROJECT" \
  | grep -v '^openinference-instrumentation-[a-z0-9-]*\s*=' \
  | sort -u)
echo "$DECLARED_PACKAGES"

echo ""
echo "Diffing..."
NEW_PACKAGES=$(comm -23 \
  <(echo "$PYPI_PACKAGES" | sort) \
  <(echo "$DECLARED_PACKAGES" | sort))

if [ -z "$NEW_PACKAGES" ]; then
  echo "No new openinference instrumentors found on PyPI. pyproject.toml is up to date."
  exit 0
else
  echo "WARNING: The following openinference instrumentors are on PyPI but not in pyproject.toml:"
  echo "$NEW_PACKAGES"
  echo ""
  echo "Please evaluate these packages and add them as optional extras in pyproject.toml"
  echo "if they are relevant. Then re-run this script to verify."
  exit 1
fi
