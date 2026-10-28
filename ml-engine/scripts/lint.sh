uv sync --frozen --group linters
uv run autoflake --remove-all-unused-imports --in-place --recursive src/ml_engine
uv run isort src/ml_engine --profile black
uv run black src/ml_engine
uv run mypy src/ml_engine scripts/jamf_smoke.py scripts/vendor_ai_detection_spec.py
