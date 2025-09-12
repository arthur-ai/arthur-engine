import pathlib

from arthur_common.config.config import Config as arthur_common_config
from simple_settings import LazySettings

# get the current directory of this file
directory = pathlib.Path(__file__).parent.resolve()

# create settings object that reads from settings.yaml and takes overrides from env
# can also be overwritten via the CLI
# https://github.com/drgarcia1986/simple-settings
settings = LazySettings(f"{directory}/settings.yaml", ".environ")


class Config:
    settings = settings

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        settings_dict = cls.settings.as_dict()
        value = settings_dict.get(key)
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        if isinstance(value, str):
            return value.lower() in ["true", "1", "yes"]
        raise ValueError(f"Invalid value for {key}: {value}")

    @staticmethod
    def segmentation_col_count_limit() -> int:
        return arthur_common_config.convert_to_int(
            settings.SEGMENTATION_COL_COUNT_LIMIT,
            "SEGMENTATION_COL_COUNT_LIMIT",
        )

    @staticmethod
    def aggregation_timeout() -> int:
        return arthur_common_config.convert_to_int(
            settings.ML_ENGINE_AGGREGATION_TIMEOUT,
            "ML_ENGINE_AGGREGATION_TIMEOUT",
        )

    @staticmethod
    def default_thread_pool_max_workers() -> int:
        return arthur_common_config.convert_to_int(
            settings.ML_ENGINE_DEFAULT_THREAD_POOL_MAX_WORKERS,
            "ML_ENGINE_DEFAULT_THREAD_POOL_MAX_WORKERS",
        )
