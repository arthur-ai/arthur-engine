#!/usr/bin/env bash
# CI script: diffs npm @arizeai/openinference-instrumentation-* packages against package.json.
# Exits 0 if nothing new, exits 1 with warning if new packages exist on npm.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_JSON="$SCRIPT_DIR/../typescript/package.json"

echo "Fetching @arizeai/openinference-instrumentation-* packages from npm..."
NPM_PACKAGES=$(npm search @arizeai/openinference-instrumentation --json 2>/dev/null \
  | node -e "
    const data = JSON.parse(require('fs').readFileSync('/dev/stdin', 'utf8'));
    data
      .map(p => p.name)
      .filter(n => n.startsWith('@arizeai/openinference-instrumentation-'))
      .sort()
      .forEach(n => console.log(n));
  ")

echo "Packages found on npm:"
echo "$NPM_PACKAGES"

echo ""
echo "Packages declared in package.json:"
DECLARED_PACKAGES=$(grep -oE '"@arizeai/openinference-instrumentation-[a-z0-9-]+"' "$PACKAGE_JSON" \
  | tr -d '"' \
  | sort -u)
echo "$DECLARED_PACKAGES"

echo ""
echo "Diffing..."
NEW_PACKAGES=$(comm -23 \
  <(echo "$NPM_PACKAGES" | sort) \
  <(echo "$DECLARED_PACKAGES" | sort))

if [ -z "$NEW_PACKAGES" ]; then
  echo "No new openinference instrumentors found on npm. package.json is up to date."
  exit 0
else
  echo "WARNING: The following openinference instrumentors are on npm but not in package.json:"
  echo "$NEW_PACKAGES"
  echo ""
  echo "Please evaluate these packages and add them as optional peer dependencies in package.json"
  echo "if they are relevant. Then re-run this script to verify."
  exit 1
fi
