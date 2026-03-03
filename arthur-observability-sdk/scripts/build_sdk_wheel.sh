#!/usr/bin/env bash
#
# build_sdk_wheel.sh [OUTPUT_DIR]
#
# Builds the arthur-observability-sdk wheel and writes it to OUTPUT_DIR
# (default: <sdk-root>/dist/).  Prints the absolute path of the built wheel
# to stdout on success.
#
# Why the temp-copy approach:
#   Poetry uses `git ls-files` when building inside a git repository, which
#   silently excludes gitignored files — including src/arthur_genai_client/.
#   By copying the SDK to a directory with no .git ancestor, poetry falls back
#   to pure filesystem discovery and includes all files listed under [packages].

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SDK_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${1:-$SDK_ROOT/dist}"

# Verify the generated client exists before attempting a build.
CLIENT_DIR="$SDK_ROOT/src/arthur_genai_client"
if [ ! -d "$CLIENT_DIR" ] || [ -z "$(find "$CLIENT_DIR" -name "*.py" 2>/dev/null | head -1)" ]; then
    echo "ERROR: src/arthur_genai_client not found or empty." >&2
    echo "Run: ./scripts/generate_openapi_client.sh generate python" >&2
    exit 1
fi

# Create a temp build dir isolated from .git.
TMP_BUILD=$(mktemp -d)
trap 'rm -rf "$TMP_BUILD"' EXIT
BUILD_DIR="$TMP_BUILD/sdk"

# Use the Python interpreter that is already active (works inside a venv or
# system Python) to copy the tree, avoiding a dependency on rsync.
python3 - <<PYEOF
import shutil, sys
shutil.copytree(
    "$SDK_ROOT",
    "$BUILD_DIR",
    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "dist", ".pytest_cache"),
)
PYEOF

# Build the wheel inside the git-free copy.
poetry -C "$BUILD_DIR" build -q --format wheel

# Locate the newest wheel in the build output.
WHEEL=$(ls -t "$BUILD_DIR/dist/"*.whl 2>/dev/null | head -1)
if [ -z "$WHEEL" ]; then
    echo "ERROR: No wheel found in dist/ after build." >&2
    exit 1
fi

# Copy the wheel to the requested output directory.
mkdir -p "$OUTPUT_DIR"
WHEEL_NAME=$(basename "$WHEEL")
cp "$WHEEL" "$OUTPUT_DIR/$WHEEL_NAME"

echo "$OUTPUT_DIR/$WHEEL_NAME"
