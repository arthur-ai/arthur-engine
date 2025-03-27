#!/usr/bin/env bash

set -ex

rm -rf src
mkdir -p src/schemas
mkdir -p src/utils
cp ../src/schemas/enums.py ./src/schemas/
cp ../src/schemas/common_schemas.py ./src/schemas/
cp ../src/schemas/response_schemas.py ./src/schemas/
cp ../src/utils/constants.py ./src/utils/

zip -r genai-engine-perf.zip . -x "genai-engine-perf.zip" -x "*/__pycache__/*" -x "__pycache__/*" -x ".DS_Store" -x "assemble.sh"
