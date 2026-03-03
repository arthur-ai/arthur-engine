#!/bin/bash

set -e

cd "$(dirname "$0")/.."

poetry run black src tests
poetry run autoflake --remove-all-unused-imports --in-place --recursive --quiet src tests
poetry run isort src tests --profile black
poetry run mypy src/arthur_observability_sdk
