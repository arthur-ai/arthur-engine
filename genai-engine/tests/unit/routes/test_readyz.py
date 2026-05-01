"""Tests for the /health (liveness) and /readyz (readiness) routes."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from services.model_warmup_service import ModelKey, ModelLoadStatus, ModelWarmupService
from tests.clients.base_test_client import GenaiEngineTestClientBase


def _service_with_state(
    statuses: dict[ModelKey, ModelLoadStatus],
) -> ModelWarmupService:
    service = ModelWarmupService()
    for key, status in statuses.items():
        service._states[key] = service._states.get(key, _make_record(key))
        service._states[key].status = status
    return service


def _make_record(key: ModelKey):
    from services.model_warmup_service import ModelStateRecord

    return ModelStateRecord(key=key)


@pytest.mark.unit_tests
def test_health_endpoint_always_returns_200(
    client: GenaiEngineTestClientBase,
) -> None:
    response = client.base_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "ok"


@pytest.mark.unit_tests
def test_readyz_returns_503_while_warming(
    client: GenaiEngineTestClientBase,
) -> None:
    warming_service = _service_with_state(
        {
            ModelKey.PROMPT_INJECTION: ModelLoadStatus.READY,
            ModelKey.TOXICITY: ModelLoadStatus.DOWNLOADING,
        },
    )
    with patch(
        "routers.health_routes.get_model_warmup_service",
        return_value=warming_service,
    ):
        response = client.base_client.get("/readyz")
    assert response.status_code == 503
    assert "Retry-After" in response.headers
    payload = response.json()
    assert payload["overall_status"] == "warming"


@pytest.mark.unit_tests
def test_readyz_returns_200_once_all_models_ready(
    client: GenaiEngineTestClientBase,
) -> None:
    ready_service = _service_with_state(
        {
            ModelKey.PROMPT_INJECTION: ModelLoadStatus.READY,
            ModelKey.TOXICITY: ModelLoadStatus.READY,
            ModelKey.PROFANITY: ModelLoadStatus.SKIPPED,
        },
    )
    with patch(
        "routers.health_routes.get_model_warmup_service",
        return_value=ready_service,
    ):
        response = client.base_client.get("/readyz")
    assert response.status_code == 200
    assert "Retry-After" not in response.headers
    assert response.json()["overall_status"] == "ready"
