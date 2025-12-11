#!/bin/bash

set -e

poetry run black src
poetry run autoflake --remove-all-unused-imports --in-place --recursive --quiet src
poetry run isort src --profile black
poetry run mypy src
