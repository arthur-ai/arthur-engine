from genai_engine.utils.utils import get_postgres_connection_string
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import StaticPool


class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    POSTGRES_DB: str | None = None
    POSTGRES_URL: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_PORT: int | str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_USE_SSL: bool = False
    POSTGRES_CLIENT_CONNECTION_POOL_SIZE: int = 5
    POSTGRES_CLIENT_CONNECTION_POOL_MAX_OVERFLOW: int = 15
    TEST_DATABASE: bool = False

    @property
    def url(self) -> str:
        if self.TEST_DATABASE:
            return "sqlite+pysqlite:///:memory:"
        return get_postgres_connection_string(
            use_ssl=self.POSTGRES_USE_SSL,
            ssl_key_path="postgres-cert.pem" if self.POSTGRES_USE_SSL else None,
        )

    def get_connection_params(self) -> dict:
        params = {
            "url": self.url,
            "echo": False,
            "future": True,
        }
        if not self.TEST_DATABASE:
            params.update(
                {
                    "pool_size": self.POSTGRES_CLIENT_CONNECTION_POOL_SIZE,
                    "max_overflow": self.POSTGRES_CLIENT_CONNECTION_POOL_MAX_OVERFLOW,
                    "pool_pre_ping": True,
                    "pool_recycle": 3600,
                    "connect_args": {
                        "keepalives": 1,
                        "keepalives_idle": 30,
                        "keepalives_interval": 10,
                        "keepalives_count": 5,
                    },
                },
            )
            if self.POSTGRES_USE_SSL:
                params["connect_args"]["sslrootcert"] = "postgres-cert.pem"
        else:
            params.update(
                {
                    "url": "sqlite+pysqlite:///:memory:",
                    "connect_args": {
                        "check_same_thread": False,
                    },
                    "poolclass": StaticPool,
                },
            )
        return params

    @model_validator(mode="after")
    def validate_parameters(self):
        if not self.TEST_DATABASE:
            if not all(
                [
                    self.POSTGRES_DB,
                    self.POSTGRES_URL,
                    self.POSTGRES_PASSWORD,
                    self.POSTGRES_PORT,
                    self.POSTGRES_USER,
                ],
            ):
                raise ValueError(
                    "POSTGRES_DB, POSTGRES_URL, POSTGRES_PASSWORD, POSTGRES_PORT, and POSTGRES_USER must be provided when TEST_DATABASE is False",
                )
        return self

    @field_validator("POSTGRES_PORT")
    def validate_postgres_port(cls, v):
        if not v:
            return None
        elif isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                raise ValueError("POSTGRES_PORT must be an integer or a string")
        elif isinstance(v, int):
            return v
        else:
            raise ValueError("POSTGRES_PORT must be an integer or a string")
