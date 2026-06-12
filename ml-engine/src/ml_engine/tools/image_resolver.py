from logging import Logger

from arthur_client.api_bindings import ConnectorSpec, ConnectorType
from arthur_common.models.connectors import BUCKET_BASED_CONNECTOR_BUCKET_FIELD

from tools.connector_constructor import ConnectorConstructor
from tools.image_tools import (
    get_bucket_from_uri,
    get_connector_type_for_image_uri,
)


class ImageResolver:
    def __init__(
        self,
        connector_constructor: ConnectorConstructor,
        project_id: str,
        logger: Logger,
    ) -> None:
        self.connector_constructor = connector_constructor
        self.project_id = project_id
        self.logger = logger
        self.connectors_for_type: dict[ConnectorType, list[ConnectorSpec]] = {}
        self.connectors_for_bucket: dict[str, list[ConnectorSpec]] = {}

    def resolve_image(self, image_uri: str) -> str:
        matches = self.get_connectors_for_image(image_uri)
        if len(matches) > 1:
            self.logger.warning(
                f"Ambiguous image_uri {image_uri} matched {len(matches)} connectors",
            )
        elif len(matches) == 0:
            self.logger.error(f"No connectors found for image {image_uri}")
            return image_uri

        for connector_spec in matches:
            try:
                connector = self.connector_constructor.get_connector_from_spec(
                    connector_spec.id,
                )
                return connector.extract_image(image_uri)
            except Exception:
                continue

        self.logger.error(f"Could not read image {image_uri}")
        return image_uri  # All failed

    def get_connectors_for_image(self, image_uri: str) -> list[ConnectorSpec]:
        connector_type = get_connector_type_for_image_uri(image_uri)
        if not connector_type:
            return []

        bucket = get_bucket_from_uri(image_uri)
        if not bucket:
            return []

        if bucket in self.connectors_for_bucket:
            return self.connectors_for_bucket[bucket]

        if connector_type not in self.connectors_for_type:
            self.connectors_for_type[connector_type] = (
                self.connector_constructor.get_connectors_for_type(
                    self.project_id,
                    connector_type,
                )
            )

        connectors_for_bucket = []
        for connector in self.connectors_for_type[connector_type]:
            for f in connector.fields:
                if f.key == BUCKET_BASED_CONNECTOR_BUCKET_FIELD and f.value == bucket:
                    connectors_for_bucket.append(connector)

        self.connectors_for_bucket[bucket] = connectors_for_bucket
        return connectors_for_bucket
