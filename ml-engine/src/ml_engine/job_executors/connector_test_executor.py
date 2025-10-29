import logging

from arthur_client.api_bindings import (
    ConnectorCheckJobSpec,
    ConnectorCheckOutcome,
    ConnectorCheckResult,
    ConnectorsV1Api,
)

from connectors.connector import Connector
from tools.connector_constructor import ConnectorConstructor


class ConnectorTestExecutor:
    def __init__(
        self,
        connectors_client: ConnectorsV1Api,
        connector_constructor: ConnectorConstructor,
        logger: logging.Logger,
    ) -> None:
        self.connectors_client: ConnectorsV1Api = connectors_client
        self.connector_constructor: ConnectorConstructor = connector_constructor
        self.logger: logging.Logger = logger

    def execute(self, job_spec: ConnectorCheckJobSpec) -> None:
        self.logger.info(
            f"Executing connector test job for connector {job_spec.connector_id}",
        )
        try:
            conn: Connector = self.connector_constructor.get_connector_from_spec(
                job_spec.connector_id,
            )
            result: ConnectorCheckResult = conn.test_connection()
            self.logger.info(f"Connector test completed for {job_spec.connector_id}")
        except Exception as e:
            self.logger.error(
                f"Connector test failed for {job_spec.connector_id}: {str(e)}",
            )
            result = ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason=str(e),
            )

        self._put_connector_check_results(job_spec.connector_id, result)

        self.logger.info(f"Connector test job completed for {job_spec.connector_id}")

    def _put_connector_check_results(
        self,
        connector_id: str,
        result: ConnectorCheckResult,
    ) -> None:
        try:
            self.connectors_client.put_connector_check_results(
                connector_id=connector_id,
                connector_check_result=result,
            )
            self.logger.info(f"Connector check results stored for {connector_id}")
        except Exception as e:
            self.logger.error(
                f"Failed to store connector check results for {connector_id}: {str(e)}",
            )
