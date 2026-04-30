"""Unit-test-wide helpers for stubbing the model warmup service."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


def stub_warmup_ready(monkeypatch: Any, *module_paths: str) -> MagicMock:
    """Patch ``get_model_warmup_service`` in each module path to a fake that
    unconditionally reports every model ready.

    Tests that exercise real model behavior on locally-loaded weights need
    the warmup gate to short-circuit, otherwise scorers would return
    ``MODEL_NOT_AVAILABLE`` before they ever touch the model. This helper
    centralizes that stub so individual test modules don't each duplicate
    the same MagicMock + monkeypatch incantation.

    Returns the underlying ``MagicMock`` so callers can assert on it if
    needed.
    """
    fake = MagicMock()
    fake.is_ready.return_value = True
    for module_path in module_paths:
        monkeypatch.setattr(
            f"{module_path}.get_model_warmup_service",
            lambda fake=fake: fake,
        )
    return fake
