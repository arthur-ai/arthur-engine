#!/usr/bin/env bash

set -ex

rm -rf genai_engine
mkdir -p genai_engine/schemas
mkdir -p genai_engine/utils
cp ../genai_engine/schemas/enums.py ./genai_engine/schemas/
cp ../genai_engine/schemas/common_schemas.py ./genai_engine/schemas/
cp ../genai_engine/schemas/response_schemas.py ./genai_engine/schemas/
cp ../genai_engine/utils/constants.py ./genai_engine/utils/

zip -r genai-engine-perf.zip . -x "genai-engine-perf.zip" -x "*/__pycache__/*" -x "__pycache__/*" -x ".DS_Store" -x "assemble.sh"
