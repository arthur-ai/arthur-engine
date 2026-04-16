from unittest.mock import patch

import pytest

from config import Config


def test_get_bool():
    with patch("config.Config.settings") as mock_settings:
        mock_settings.as_dict.return_value = {"FETCH_RAW_DATA_ENABLED": "true"}
        assert Config.get_bool("FETCH_RAW_DATA_ENABLED", default=True) is True

    with patch("config.Config.settings") as mock_settings:
        mock_settings.as_dict.return_value = {"FETCH_RAW_DATA_ENABLED": "false"}
        assert Config.get_bool("FETCH_RAW_DATA_ENABLED", default=True) is False

    with patch("config.Config.settings") as mock_settings:
        mock_settings.as_dict.return_value = {}
        assert Config.get_bool("FETCH_RAW_DATA_ENABLED", default=True) is True

    with patch("config.Config.settings") as mock_settings:
        mock_settings.as_dict.return_value = {"FETCH_RAW_DATA_ENABLED": 123}
        with pytest.raises(ValueError):
            Config.get_bool("FETCH_RAW_DATA_ENABLED", default=True)


def test_genai_engine_max_page_size():
    with patch("config.config.settings") as mock_settings:
        mock_settings.GENAI_ENGINE_MAX_PAGE_SIZE = 500
        assert Config.genai_engine_max_page_size() == 500

    # env vars arrive as strings — verify string coercion works
    with patch("config.config.settings") as mock_settings:
        mock_settings.GENAI_ENGINE_MAX_PAGE_SIZE = "750"
        assert Config.genai_engine_max_page_size() == 750
