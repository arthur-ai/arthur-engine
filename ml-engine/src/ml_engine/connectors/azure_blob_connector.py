from dataclasses import dataclass
from logging import Logger
from typing import Optional

from adlfs import AzureBlobFileSystem
from arthur_client.api_bindings import ConnectorSpec
from arthur_common.models.connectors import (
    AZURE_CONNECTOR_ACCOUNT_KEY_FIELD,
    AZURE_CONNECTOR_ACCOUNT_NAME_FIELD,
    AZURE_CONNECTOR_CLIENT_ID_FIELD,
    AZURE_CONNECTOR_CLIENT_SECRET_FIELD,
    AZURE_CONNECTOR_CONNECTION_STRING_FIELD,
    AZURE_CONNECTOR_SAS_TOKEN_FIELD,
    AZURE_CONNECTOR_TENANT_ID_FIELD,
)

from connectors.bucket_based_connector import BucketBasedConnector


@dataclass
class _AzureConnectorConfigFields:
    account_name: Optional[str]
    account_key: Optional[str]
    sas_token: Optional[str]
    connection_string: Optional[str]
    tenant_id: Optional[str]
    client_id: Optional[str]
    client_secret: Optional[str]


class AzureBlobConnector(BucketBasedConnector):
    def __init__(self, connector_config: ConnectorSpec, logger: Logger) -> None:
        config = self._extract_connector_config_fields(connector_config)
        self.fs = self._construct_adlfs_with_auth(config)
        super().__init__(logger, connector_config)

    @staticmethod
    def _extract_connector_config_fields(
        connector_config: ConnectorSpec,
    ) -> _AzureConnectorConfigFields:
        fields = {f.key: f.value for f in connector_config.fields}
        return _AzureConnectorConfigFields(
            account_name=fields.get(AZURE_CONNECTOR_ACCOUNT_NAME_FIELD),
            account_key=fields.get(AZURE_CONNECTOR_ACCOUNT_KEY_FIELD),
            sas_token=fields.get(AZURE_CONNECTOR_SAS_TOKEN_FIELD),
            connection_string=fields.get(AZURE_CONNECTOR_CONNECTION_STRING_FIELD),
            tenant_id=fields.get(AZURE_CONNECTOR_TENANT_ID_FIELD),
            client_id=fields.get(AZURE_CONNECTOR_CLIENT_ID_FIELD),
            client_secret=fields.get(AZURE_CONNECTOR_CLIENT_SECRET_FIELD),
        )

    @staticmethod
    def _construct_adlfs_with_auth(
        config: _AzureConnectorConfigFields,
    ) -> AzureBlobFileSystem:
        if config.connection_string:
            return AzureBlobFileSystem(connection_string=config.connection_string)
        if config.tenant_id and config.client_id and config.client_secret:
            if not config.account_name:
                raise ValueError("account_name is required for service principal auth")
            return AzureBlobFileSystem(
                account_name=config.account_name,
                tenant_id=config.tenant_id,
                client_id=config.client_id,
                client_secret=config.client_secret,
            )
        if config.sas_token:
            if not config.account_name:
                raise ValueError("account_name is required for SAS token auth")
            return AzureBlobFileSystem(
                account_name=config.account_name,
                sas_token=config.sas_token,
            )
        if config.account_name and config.account_key:
            return AzureBlobFileSystem(
                account_name=config.account_name,
                account_key=config.account_key,
            )
        raise ValueError(
            "At least one auth method is required: connection_string, "
            "service principal (tenant_id+client_id+client_secret+account_name), "
            "sas_token+account_name, or account_name+account_key",
        )

    @property
    def file_system(self) -> AzureBlobFileSystem:
        return self.fs
