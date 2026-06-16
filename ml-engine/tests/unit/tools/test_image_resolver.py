import logging
from unittest.mock import Mock

from arthur_client.api_bindings import ConnectorType
from arthur_common.models.connectors import BUCKET_BASED_CONNECTOR_BUCKET_FIELD

from tools.image_resolver import ImageResolver

LOGGER = logging.getLogger(__name__)


def make_connector_spec(connector_id: str, bucket: str) -> Mock:
    field = Mock()
    field.key = BUCKET_BASED_CONNECTOR_BUCKET_FIELD
    field.value = bucket
    spec = Mock()
    spec.id = connector_id
    spec.fields = [field]
    return spec


def test_resolve_image_success() -> None:
    spec = make_connector_spec("c1", "my-bucket")
    connector = Mock()
    connector.extract_image.return_value = "base64data"

    constructor = Mock()
    constructor.get_connectors_for_type.return_value = [spec]
    constructor.get_connector_from_spec.return_value = connector

    resolver = ImageResolver(constructor, "project-1", LOGGER)
    result = resolver.resolve_image("gs://my-bucket/img.png")

    assert result == "base64data"
    constructor.get_connectors_for_type.assert_called_once_with(
        "project-1",
        ConnectorType.GCS,
    )
    connector.extract_image.assert_called_once_with("gs://my-bucket/img.png")


def test_resolve_image_no_connectors_returns_uri() -> None:
    constructor = Mock()
    constructor.get_connectors_for_type.return_value = []

    resolver = ImageResolver(constructor, "project-1", LOGGER)
    uri = "gs://missing-bucket/img.png"

    assert resolver.resolve_image(uri) == uri
    constructor.get_connector_from_spec.assert_not_called()


def test_resolve_image_unsupported_uri_returns_uri() -> None:
    constructor = Mock()
    resolver = ImageResolver(constructor, "project-1", LOGGER)
    uri = "unsupported_uri://bucket/img.png"

    assert resolver.resolve_image(uri) == uri
    constructor.get_connectors_for_type.assert_not_called()


def test_resolve_image_falls_back_on_extract_failure() -> None:
    spec = make_connector_spec("c1", "my-bucket")
    connector = Mock()
    connector.extract_image.side_effect = Exception("read failed")

    constructor = Mock()
    constructor.get_connectors_for_type.return_value = [spec]
    constructor.get_connector_from_spec.return_value = connector

    resolver = ImageResolver(constructor, "project-1", LOGGER)
    uri = "gs://my-bucket/img.png"

    assert resolver.resolve_image(uri) == uri


def test_resolve_image_tries_next_connector_on_failure() -> None:
    spec1 = make_connector_spec("c1", "my-bucket")
    spec2 = make_connector_spec("c2", "my-bucket")

    failing_connector = Mock()
    failing_connector.extract_image.side_effect = Exception("read failed")
    working_connector = Mock()
    working_connector.extract_image.return_value = "base64data"

    constructor = Mock()
    constructor.get_connectors_for_type.return_value = [spec1, spec2]
    constructor.get_connector_from_spec.side_effect = [
        failing_connector,
        working_connector,
    ]

    resolver = ImageResolver(constructor, "project-1", LOGGER)
    assert resolver.resolve_image("gs://my-bucket/img.png") == "base64data"


def test_connectors_cached_per_bucket() -> None:
    spec = make_connector_spec("c1", "my-bucket")
    connector = Mock()
    connector.extract_image.return_value = "base64data"

    constructor = Mock()
    constructor.get_connectors_for_type.return_value = [spec]
    constructor.get_connector_from_spec.return_value = connector

    resolver = ImageResolver(constructor, "project-1", LOGGER)
    resolver.resolve_image("gs://my-bucket/img1.png")
    resolver.resolve_image("gs://my-bucket/img2.png")

    # connectors fetched only once for the same bucket
    constructor.get_connectors_for_type.assert_called_once()


def test_connectors_filtered_by_bucket() -> None:
    spec_match = make_connector_spec("c1", "my-bucket")
    spec_other = make_connector_spec("c2", "other-bucket")

    constructor = Mock()
    constructor.get_connectors_for_type.return_value = [spec_match, spec_other]

    resolver = ImageResolver(constructor, "project-1", LOGGER)
    matches = resolver.get_connectors_for_image("gs://my-bucket/img.png")

    assert matches == [spec_match]
