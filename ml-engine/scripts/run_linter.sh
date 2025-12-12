#!/bin/bash

set -e

poetry run black src/ml_engine
poetry run autoflake --remove-all-unused-imports --in-place --recursive --quiet src/ml_engine
poetry run isort src/ml_engine --profile black
poetry run mypy src/ml_engine
