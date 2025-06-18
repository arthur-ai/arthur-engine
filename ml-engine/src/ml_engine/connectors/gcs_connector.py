import json
from logging import Logger

import gcsfs
from arthur_client.api_bindings import ConnectorSpec
from arthur_common.models.connectors import (
    GOOGLE_CONNECTOR_CREDENTIALS_FIELD,
    GOOGLE_CONNECTOR_LOCATION_FIELD,
    GOOGLE_CONNECTOR_PROJECT_ID_FIELD,
)
from connectors.bucket_based_connector import BucketBasedConnector


class GCSConnector(BucketBasedConnector):
    def __init__(self, connector_config: ConnectorSpec, logger: Logger) -> None:
        connector_fields = {f.key: f.value for f in connector_config.fields}
        creds = connector_fields.get(GOOGLE_CONNECTOR_CREDENTIALS_FIELD)
        token = json.loads(creds) if creds else None
        location = connector_fields.get(GOOGLE_CONNECTOR_LOCATION_FIELD)

        self.fs = gcsfs.GCSFileSystem(
            project=str(connector_fields[GOOGLE_CONNECTOR_PROJECT_ID_FIELD]),
            access="read_only",
            token=token,
            default_location=location,
        )
        super().__init__(logger, connector_config)

    @property
    def file_system(self) -> gcsfs.GCSFileSystem:
        return self.fs
