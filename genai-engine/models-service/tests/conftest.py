"""Shared pytest config for the models service.

These tests exercise the inference modules directly with real models —
behavioural coverage for the torch/transformers pipelines. Two markers:

- @pytest.mark.unit_tests — pure unit tests (no model weights required;
  e.g. regex profanity, Presidio-only PII v1, validation logic).
- @pytest.mark.real_models — needs torch/transformers weights loaded.
  Fast CI can skip with `-m "not real_models"`.
"""

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "unit_tests: pure unit tests (no model weights required)",
    )
    config.addinivalue_line(
        "markers",
        "real_models: requires real torch/transformers weights — skip in fast CI",
    )


@pytest.fixture(autouse=True)
def _disable_skip_loading():
    # Tests that need real models should run without the skip flag.
    prev = os.environ.pop("MODELS_SERVICE_SKIP_LOADING", None)
    try:
        yield
    finally:
        if prev is not None:
            os.environ["MODELS_SERVICE_SKIP_LOADING"] = prev
