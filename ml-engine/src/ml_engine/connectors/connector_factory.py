from logging import Logger
from typing import Dict, Type

from arthur_client.api_bindings import ConnectorSpec, ConnectorType

from .connector import Connector
from .odbc_connector import ODBCConnector
from .snowflake_connector import SnowflakeConnector


class ConnectorFactory:
    """
    Factory class for creating connector instances based on configuration.
    """

    _connector_registry: Dict[ConnectorType, Type[Connector]] = {
        ConnectorType.SNOWFLAKE: SnowflakeConnector,
        ConnectorType.ODBC: ODBCConnector,
    }

    @classmethod
    def create_connector(
        cls,
        connector_config: ConnectorSpec,
        logger: Logger,
    ) -> Connector:
        """
        Create a connector instance based on the configuration.

        Args:
            connector_config: The connector configuration specification
            logger: Logger instance for the connector

        Returns:
            An instance of the appropriate connector class

        Raises:
            ValueError: If no suitable connector is found for the configuration
        """
        # Get connector type from configuration
        connector_type = connector_config.connector_type

        # Find the appropriate connector class
        connector_class = cls._connector_registry.get(connector_type)

        # If no specific connector type found, default to ODBCConnector
        if connector_class is None:
            connector_class = ODBCConnector

        # Create and return the connector instance
        return connector_class(connector_config, logger)

    @classmethod
    def register_connector(
        cls,
        connector_type: ConnectorType,
        connector_class: Type[Connector],
    ) -> None:
        """
        Register a new connector class for a specific connector type.

        Args:
            connector_type: The connector type to register
            connector_class: The connector class to use for this type
        """
        cls._connector_registry[connector_type] = connector_class

    @classmethod
    def get_available_connectors(cls) -> Dict[str, str]:
        """
        Get a mapping of available connector types to connector class names.

        Returns:
            Dictionary mapping connector types to connector class names
        """
        return {
            connector_type.value: connector_class.__name__
            for connector_type, connector_class in cls._connector_registry.items()
        }
