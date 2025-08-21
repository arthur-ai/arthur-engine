from logging import Logger

from arthur_client.api_bindings import ConnectorsV1Api, ConnectorType
from connectors.big_query_connector import BigQueryConnector
from connectors.connector import Connector
from connectors.connector_factory import ConnectorFactory
from connectors.gcs_connector import GCSConnector
from connectors.odbc_connector import ODBCConnector
from connectors.s3_connector import S3Connector
from connectors.shield_connector import EngineInternalConnector, ShieldConnector


class ConnectorConstructor:
    def __init__(self, connectors_client: ConnectorsV1Api, scope_logger: Logger):
        self.connectors_client = connectors_client
        self.scope_logger = scope_logger

    def get_connector_from_spec(self, connector_id: str) -> Connector:
        connector_config = self.connectors_client.get_sensitive_connector(connector_id)
        match connector_config.connector_type:
            case ConnectorType.SHIELD:
                return ShieldConnector(connector_config, self.scope_logger)
            case ConnectorType.S3:
                return S3Connector(connector_config, self.scope_logger)
            case ConnectorType.GCS:
                return GCSConnector(connector_config, self.scope_logger)
            case ConnectorType.BIGQUERY:
                return BigQueryConnector(connector_config, self.scope_logger)
            case ConnectorType.ENGINE_INTERNAL:
                return EngineInternalConnector(connector_config, self.scope_logger)
            case ConnectorType.ODBC:
                return ODBCConnector(connector_config, self.scope_logger)
            case ConnectorType.SNOWFLAKE:
                return ConnectorFactory.create_connector(
                    connector_config,
                    self.scope_logger,
                )
            case _:
                raise NotImplementedError(
                    f"Connector not available for type {connector_config.connector_type}",
                )
