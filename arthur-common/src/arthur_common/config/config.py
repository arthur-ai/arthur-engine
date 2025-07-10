# get the current directory of this file
import logging
import pathlib

directory = pathlib.Path(__file__).parent.resolve()

# create settings object that reads from settings.yaml and takes overrides from env
# can also be overwritten via the CLI
# https://github.com/drgarcia1986/simple-settings
from simple_settings import LazySettings

settings = LazySettings(f"{directory}/settings.yaml", ".environ")

logger = logging.getLogger()


class Config:
    settings = settings

    @staticmethod
    def convert_to_int(value: str | int, setting_name: str) -> int:
        if isinstance(value, int):
            return value
        elif value == "":
            raise ValueError(
                f"Config setting {setting_name} could not be cast to an int.",
            )

        # attempt to convert setting to int
        try:
            return int(value.strip())
        except TypeError:
            raise ValueError(
                f"Config setting {setting_name} could not be cast to an int.",
            )

    @staticmethod
    def segmentation_col_unique_values_limit() -> int:
        return Config.convert_to_int(
            settings.SEGMENTATION_COL_UNIQUE_VALUE_LIMIT,
            "SEGMENTATION_COL_UNIQUE_VALUE_LIMIT",
        )
