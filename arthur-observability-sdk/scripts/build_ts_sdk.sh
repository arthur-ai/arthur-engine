#!/usr/bin/env bash
#
# build_ts_sdk.sh
#
# Canonical script for building the TypeScript Arthur Observability SDK.
# Produces dist/ and a .tgz tarball in the typescript/ directory.
#
# Usage:
#   ./scripts/build_ts_sdk.sh
#
# To run checks locally before committing:
#   cd typescript
#   npm run type-check   # TypeScript type checking
#   npm run lint         # ESLint
#   npm run format:check # Prettier
#   npm test             # Unit tests

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TS_DIR="$SCRIPT_DIR/../typescript"

if [ ! -f "$TS_DIR/package.json" ]; then
  echo "ERROR: typescript/package.json not found at $TS_DIR" >&2
  exit 1
fi

cd "$TS_DIR"

echo "==> Installing dependencies..."
npm ci --no-fund --no-audit

echo "==> Building..."
npm run build

echo "==> Packing tarball..."
npm pack

echo "==> Done. Artifacts in $TS_DIR/dist/ and $TS_DIR/*.tgz"
