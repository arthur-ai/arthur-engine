#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -eq 0 ]; then
    echo "Please provide a purpose and language runtime."
    echo "Usage: ./generate_openapi_client.sh <purpose> [<language>]"
    echo "Possible values: purpose - 'generate', 'install'; language - 'python' (default)"
    echo "No changes made. Exiting!"
    exit 2
fi

export OPENAPI_GENERATOR_VERSION=7.12.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC_PATH="$SCRIPT_DIR/../../genai-engine/staging.openapi.json"

purpose=${1:-generate}
language=${2:-python}

install_or_update_openapi_gen() {
  echo "Installing or updating openapi-generator-cli to version $OPENAPI_GENERATOR_VERSION..."
  if [[ $(uname) == 'Darwin' ]]; then
    brew install npm
    npm install -g @openapitools/openapi-generator-cli
    openapi-generator-cli version-manager set $OPENAPI_GENERATOR_VERSION
  else
    npm install -g @openapitools/openapi-generator-cli
    openapi-generator-cli version-manager set $OPENAPI_GENERATOR_VERSION
  fi
}

if [[ "$purpose" == "generate" ]]; then
  if [[ "$language" == "python" ]]; then
    # Install CLI if not present
    if ! command -v openapi-generator-cli &> /dev/null; then
      echo "openapi-generator-cli is not installed."
      install_or_update_openapi_gen
    else
      echo "openapi-generator-cli version $(openapi-generator-cli version) already installed"
    fi

    # Upgrade CLI if not on desired version
    version=$(openapi-generator-cli version)
    if [ "$version" != "$OPENAPI_GENERATOR_VERSION" ]; then
      install_or_update_openapi_gen
      openapi-generator-cli version
    fi

    if [ ! -f "$SPEC_PATH" ]; then
      echo "ERROR: OpenAPI spec not found at $SPEC_PATH"
      exit 1
    fi

    pkg_version=$(python3 -c "import tomllib; d=tomllib.load(open('$SCRIPT_DIR/../python/pyproject.toml','rb')); print(d['project']['version'])" 2>/dev/null || echo "1.0.0")

    OUTPUT_PATH="$SCRIPT_DIR/../python/src/arthur_genai_client_build"
    PACKAGE_PATH="$SCRIPT_DIR/../python/src/arthur_genai_client"

    echo "Clearing previous generated code..."
    rm -rf "$OUTPUT_PATH"
    mkdir -p "$OUTPUT_PATH"

    echo "Generating Python client from $SPEC_PATH..."
    openapi-generator-cli generate \
      -i "$SPEC_PATH" \
      --skip-validate-spec \
      -g python \
      -o "$OUTPUT_PATH" \
      --package-name arthur_genai_client \
      -p packageVersion="$pkg_version"

    echo "Copying generated package to $PACKAGE_PATH..."
    rm -rf "$PACKAGE_PATH"
    cp -r "$OUTPUT_PATH/arthur_genai_client" "$PACKAGE_PATH"
    rm -rf "$OUTPUT_PATH"

    echo "Client generated successfully at $PACKAGE_PATH"
  else
    echo "Unsupported language: $language"
    echo "Supported languages: python"
    exit 1
  fi

elif [[ "$purpose" == "install" ]]; then
  if [[ "$language" == "python" ]]; then
    echo "Installing Python client into uv environment..."
    uv sync --project "$SCRIPT_DIR/../python"
    echo "Client installed successfully."
  else
    echo "Unsupported language: $language"
    echo "Supported languages: python"
    exit 1
  fi

else
  echo "Unknown purpose: $purpose"
  echo "Usage: ./generate_openapi_client.sh <purpose> [<language>]"
  echo "Possible values: purpose - 'generate', 'install'; language - 'python' (default)"
  exit 1
fi
