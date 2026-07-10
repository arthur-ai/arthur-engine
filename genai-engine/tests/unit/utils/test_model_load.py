from unittest.mock import patch

import pytest

from utils import constants, model_load


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "value, expected",
    [
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("", False),
    ],
)
def test_models_loaded_offline_reads_env(monkeypatch, value, expected):
    monkeypatch.setenv(constants.HF_HUB_OFFLINE_ENV_VAR, value)
    assert model_load.models_loaded_offline() is expected


@pytest.mark.unit_tests
def test_models_loaded_offline_defaults_false(monkeypatch):
    monkeypatch.delenv(constants.HF_HUB_OFFLINE_ENV_VAR, raising=False)
    assert model_load.models_loaded_offline() is False


@pytest.mark.unit_tests
def test_download_models_skipped_when_offline(monkeypatch):
    """Offline mode (HF_HUB_OFFLINE) must not enumerate or download anything."""
    monkeypatch.setenv(constants.HF_HUB_OFFLINE_ENV_VAR, "1")
    monkeypatch.delenv(constants.GENAI_ENGINE_SKIP_MODEL_LOADING_ENV_VAR, raising=False)
    with (
        patch.object(model_load, "get_models_to_download") as mock_get,
        patch.object(
            model_load,
            "get_context",
        ) as mock_ctx,
    ):
        model_load.download_models(1)
    mock_get.assert_not_called()
    mock_ctx.assert_not_called()


@pytest.mark.unit_tests
def test_download_models_runs_when_online(monkeypatch):
    """Online mode (HF_HUB_OFFLINE unset) still downloads via the process pool."""
    monkeypatch.delenv(constants.HF_HUB_OFFLINE_ENV_VAR, raising=False)
    monkeypatch.delenv(constants.GENAI_ENGINE_SKIP_MODEL_LOADING_ENV_VAR, raising=False)
    with (
        patch.object(
            model_load,
            "get_models_to_download",
            return_value={"some/model": ["config.json"]},
        ) as mock_get,
        patch.object(model_load, "get_context") as mock_ctx,
    ):
        model_load.download_models(1)
    mock_get.assert_called_once()
    mock_ctx.assert_called_once_with("spawn")
