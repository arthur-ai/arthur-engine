import json
import uuid
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelemetryConfigFile(BaseModel):
    instance_id: str


class TelemetryConfig(BaseSettings):
    ENABLED: bool = Field(default=True)
    CONFIG_FILE_PATH: str = Field(
        default="~/.arthur_engine/telemetry_config.json",
    )
    INSTANCE_ID: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="TELEMETRY_",
    )

    def get_instance_id(self) -> str:
        if self.INSTANCE_ID:
            return self.INSTANCE_ID

        config_file_path = Path(self.CONFIG_FILE_PATH).expanduser()
        config_file_path.parent.mkdir(exist_ok=True)

        if config_file_path.exists():
            try:
                with config_file_path.open() as file:
                    config_data = json.load(file)
                    return config_data.get("instance_id", "default")
            except Exception as e:
                config_file_path.unlink(missing_ok=True)

        self.INSTANCE_ID = str(uuid.uuid4())
        new_config_file = TelemetryConfigFile(instance_id=self.INSTANCE_ID)
        with config_file_path.open("w+") as f:
            f.write(new_config_file.model_dump_json())
        return self.INSTANCE_ID
