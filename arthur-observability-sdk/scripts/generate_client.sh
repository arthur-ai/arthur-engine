#!/bin/bash

# Script to generate Python client from OpenAPI specification
# Uses openapi-generator to generate bindings
#
# Note: We use openapi-generator instead of openapi-python-client because it:
# - Handles schema names with hyphens (e.g., "OpenAIMessage-Output") correctly
# - Successfully parses complex schemas with circular references
# - Generates all endpoints without warnings about missing schema references
#
# This script calls post_generate.py for all Python post-processing tasks.
# See post_generate.py for details on import fixing and init file creation.

set -e

# Configuration
OPENAPI_SPEC_PATH="../genai-engine/staging.openapi.json"
OUTPUT_DIR="src/arthur_observability_sdk/_generated"
PACKAGE_NAME="arthur_observability_sdk._generated"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Generating Arthur API client from OpenAPI spec...${NC}"

# Check if openapi-generator-cli is installed
if ! command -v openapi-generator-cli &> /dev/null; then
    echo -e "${YELLOW}openapi-generator-cli not found. Installing...${NC}"
    npm install -g @openapitools/openapi-generator-cli
fi

# Remove old generated code if it exists
if [ -d "$OUTPUT_DIR" ]; then
    echo "Removing old generated client..."
    rm -rf "$OUTPUT_DIR"
fi

# Generate the client using openapi-generator
echo -e "${BLUE}Running openapi-generator-cli...${NC}"
openapi-generator-cli generate \
    -i "$OPENAPI_SPEC_PATH" \
    -g python \
    -o "$OUTPUT_DIR" \
    --package-name "$PACKAGE_NAME" \
    --skip-validate-spec \
    --additional-properties=packageName=$PACKAGE_NAME,projectName=arthur-api-client,library=urllib3

# Run post-generation processing
echo -e "${BLUE}Running post-generation processing...${NC}"
python3 scripts/post_generate.py

echo -e "${GREEN}✓ Client generation complete!${NC}"
echo -e "Generated files are in: ${BLUE}$OUTPUT_DIR${NC}"
