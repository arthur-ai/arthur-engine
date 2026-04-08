#!/bin/bash

set -e

uv run black src/ml_engine
uv run autoflake --remove-all-unused-imports --in-place --recursive --quiet src/ml_engine
uv run isort src/ml_engine --profile black
uv run mypy src/ml_engine
