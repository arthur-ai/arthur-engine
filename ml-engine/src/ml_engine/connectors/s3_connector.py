import asyncio
from dataclasses import dataclass
from logging import Logger
from typing import Optional
from uuid import UUID

import s3fs
from aiobotocore.session import get_session
from arthur_client.api_bindings import ConnectorSpec
from arthur_common.models.connectors import (
    AWS_CONNECTOR_ACCESS_KEY_ID_FIELD,
    AWS_CONNECTOR_EXTERNAL_ID_FIELD,
    AWS_CONNECTOR_REGION_FIELD,
    AWS_CONNECTOR_ROLE_ARN_FIELD,
    AWS_CONNECTOR_ROLE_DURATION_SECONDS_FIELD,
    AWS_CONNECTOR_SECRET_ACCESS_KEY_FIELD,
    S3_CONNECTOR_ENDPOINT_FIELD,
)
from connectors.bucket_based_connector import BucketBasedConnector
from tools.aws_credentials import assume_role


@dataclass
class _S3ConnectorConfigFields:
    endpoint: Optional[str]
    region: Optional[str]
    access_key_id: Optional[str]
    secret_access_key: Optional[str]
    role_arn: Optional[str]
    external_id: Optional[str]
    duration_seconds: int = 3600


class S3Connector(BucketBasedConnector):
    def __init__(self, connector_config: ConnectorSpec, logger: Logger) -> None:
        connector_config_fields = self._extract_connector_config_fields(
            connector_config,
        )
        self.fs = self._construct_s3fs_with_auth(
            connector_config_fields,
            UUID(connector_config.id),
        )
        super().__init__(logger, connector_config)

    @staticmethod
    def _extract_connector_config_fields(
        connector_config: ConnectorSpec,
    ) -> _S3ConnectorConfigFields:
        connector_fields = {f.key: f.value for f in connector_config.fields}
        return _S3ConnectorConfigFields(
            endpoint=connector_fields.get(S3_CONNECTOR_ENDPOINT_FIELD),
            region=connector_fields.get(AWS_CONNECTOR_REGION_FIELD),
            access_key_id=connector_fields.get(AWS_CONNECTOR_ACCESS_KEY_ID_FIELD),
            secret_access_key=connector_fields.get(
                AWS_CONNECTOR_SECRET_ACCESS_KEY_FIELD,
            ),
            role_arn=connector_fields.get(AWS_CONNECTOR_ROLE_ARN_FIELD),
            duration_seconds=int(
                connector_fields.get(AWS_CONNECTOR_ROLE_DURATION_SECONDS_FIELD, 3600),
            ),
            external_id=connector_fields.get(AWS_CONNECTOR_EXTERNAL_ID_FIELD),
        )

    @staticmethod
    def _construct_s3fs_with_auth(
        connector_config_fields: _S3ConnectorConfigFields,
        connector_id: UUID,
    ) -> s3fs.S3FileSystem:
        sess = get_session()
        if (
            connector_config_fields.access_key_id
            and connector_config_fields.secret_access_key
        ):
            sess.set_credentials(
                access_key=connector_config_fields.access_key_id,
                secret_key=connector_config_fields.secret_access_key,
            )
        if connector_config_fields.role_arn:
            sess = asyncio.run(
                assume_role(
                    session=sess,
                    role_arn=connector_config_fields.role_arn,
                    duration=connector_config_fields.duration_seconds,
                    external_id=connector_config_fields.external_id,
                    session_name=f"arthur_connector_{connector_id}",
                ),
            )
        return s3fs.S3FileSystem(
            endpoint_url=connector_config_fields.endpoint,
            s3_additional_kwargs={"region": connector_config_fields.region},
            session=sess,
        )

    @property
    def file_system(self) -> s3fs.S3FileSystem:
        return self.fs
