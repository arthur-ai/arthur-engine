import os
from typing import TypedDict

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from utils import constants


class BaseKeyCloakParameters(TypedDict):
    server_url: str
    realm_name: str
    verify: bool | str


class UserCredentialsKeyCloakParameters(BaseKeyCloakParameters):
    username: str
    password: str


class TokenCredentialsCloakParameters(BaseKeyCloakParameters):
    client_id: str
    client_secret_key: str


class KeyCloakSettings(BaseSettings):
    ENABLED: bool = True
    SERVER_URL: str | None = Field(alias="KEYCLOAK_HOST_URI", default=None)
    ADMIN_REALM: str = "master"
    GENAI_ENGINE_REALM: str = "genai_engine"
    REALM: str | None = None
    ADMIN_USERNAME: str | None = Field(
        alias="AUTH_ADMIN_CONSOLE_USERNAME",
        default=None,
    )
    ADMIN_PASSWORD: str | None = Field(
        alias="AUTH_ADMIN_CONSOLE_PASSWORD",
        default=None,
    )
    VERIFY_SSL: bool = (
        os.getenv(constants.GENAI_ENGINE_KEYCLOAK_VERIFY_SSL_ENV_VAR, "true").lower()
        == "true"
    )
    USE_PRIVATE_CERT: bool = False
    PRIVATE_CERT_PATH: str = "keycloak-cert.pem"
    GENAI_ENGINE_REALM_CLIENT_ID: str | None = Field(
        alias="AUTH_CLIENT_ID",
        default=None,
    )
    GENAI_ENGINE_REALM_CLIENT_SECRET: str | None = Field(
        alias="AUTH_CLIENT_SECRET",
        default=None,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="KEYCLOAK_",
    )

    @property
    def genai_engine_realm_admin_client_id(self) -> str:
        return str(self.GENAI_ENGINE_REALM_CLIENT_ID) + "-admin"

    def get_master_admin_parameters(self) -> UserCredentialsKeyCloakParameters:
        verify = self.PRIVATE_CERT_PATH if self.USE_PRIVATE_CERT else self.VERIFY_SSL
        return UserCredentialsKeyCloakParameters(
            server_url=self.SERVER_URL or "",
            realm_name=self.ADMIN_REALM or "",
            username=self.ADMIN_USERNAME or "",
            password=self.ADMIN_PASSWORD or "",
            verify=verify,
        )

    def get_genai_engine_admin_parameters(self) -> TokenCredentialsCloakParameters:
        verify = self.PRIVATE_CERT_PATH if self.USE_PRIVATE_CERT else self.VERIFY_SSL
        return TokenCredentialsCloakParameters(
            server_url=self.SERVER_URL or "",
            realm_name=self.GENAI_ENGINE_REALM or "",
            client_id=self.genai_engine_realm_admin_client_id or "",
            client_secret_key=self.GENAI_ENGINE_REALM_CLIENT_SECRET or "",
            verify=verify,
        )

    @model_validator(mode="after")
    def validate_parameters(self):
        if self.ENABLED:
            if not all(
                [
                    self.SERVER_URL,
                    self.ADMIN_REALM,
                    self.GENAI_ENGINE_REALM,
                    self.ADMIN_USERNAME,
                    self.ADMIN_PASSWORD,
                ],
            ):
                raise ValueError(
                    "SERVER_URL, ADMIN_REALM, GENAI_ENGINE_REALM, ADMIN_USERNAME, and ADMIN_PASSWORD must be provided when ENABLED is True",
                )
        return self
