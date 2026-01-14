#!/bin/bash

# Script to generate Python client from OpenAPI specification
# Uses openapi-python-client to generate bindings

set -e

# Configuration
OPENAPI_SPEC_PATH="../genai-engine/staging.openapi.json"
OUTPUT_DIR="src/arthur_observability_sdk/_generated"
PACKAGE_NAME="arthur_observability_sdk._generated"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Generating Arthur API client from OpenAPI spec...${NC}"

# Check if openapi-python-client is installed
if ! command -v openapi-python-client &> /dev/null; then
    echo "openapi-python-client not found. Installing..."
    pip install openapi-python-client>=0.21.0
fi

# Remove old generated code if it exists
if [ -d "$OUTPUT_DIR" ]; then
    echo "Removing old generated client..."
    rm -rf "$OUTPUT_DIR"
fi

# Generate the client
echo -e "${BLUE}Running openapi-python-client generate...${NC}"
openapi-python-client generate \
    --path "$OPENAPI_SPEC_PATH" \
    --output-path "$OUTPUT_DIR" \
    --config scripts/openapi-generator-config.yaml

echo -e "${GREEN}✓ Client generation complete!${NC}"
echo -e "Generated files are in: ${BLUE}$OUTPUT_DIR${NC}"
