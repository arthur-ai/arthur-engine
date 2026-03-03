#!/usr/bin/env bash
# Builds the SDK wheel, installs it into a fresh venv, and verifies imports.
# Catches packaging issues (missing bundled packages, missing dependencies)
# that unit tests running in the dev venv cannot detect.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_DIR="$SCRIPT_DIR/.."
VENV_DIR="$(mktemp -d)/install_test_venv"

cleanup() {
  echo "Cleaning up $VENV_DIR..."
  rm -rf "$VENV_DIR"
}
trap cleanup EXIT

echo "=== Building wheel ==="
cd "$SDK_DIR"
poetry build -q
WHEEL=$(ls -t dist/*.whl | head -1)
echo "Built: $WHEEL"

echo ""
echo "=== Creating fresh venv ==="
python3 -m venv "$VENV_DIR"
PIP="$VENV_DIR/bin/pip"
PYTHON="$VENV_DIR/bin/python"

echo ""
echo "=== Installing wheel into clean venv ==="
"$PIP" install --quiet "$WHEEL"

echo ""
echo "=== Verifying imports ==="
"$PYTHON" - <<'EOF'
import sys

# Core SDK
from arthur_observability_sdk import Arthur
print("  arthur_observability_sdk ... OK")

# Bundled generated client — top-level package
import arthur_genai_client
print("  arthur_genai_client ... OK")

# Generated client submodules (these were missing in packaging bugs)
from arthur_genai_client import ApiClient, Configuration
print("  arthur_genai_client.ApiClient / Configuration ... OK")

from arthur_genai_client.api.prompts_api import PromptsApi
print("  arthur_genai_client.api.prompts_api ... OK")

from arthur_genai_client.models.variable_template_value import VariableTemplateValue
print("  arthur_genai_client.models ... OK")

# Generated client runtime dependencies
import dateutil
import urllib3
print("  dateutil, urllib3 ... OK")

# OTel
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
print("  opentelemetry ... OK")

# Smoke test: construct Arthur without telemetry
arthur = Arthur(service_name="install-test", enable_telemetry=False)
arthur.shutdown()
print("  Arthur(service_name=...) instantiation ... OK")

print("")
print("All install checks passed.")
EOF

echo ""
echo "=== Install test PASSED ==="
