import logging
from unittest.mock import Mock, patch

from arthur_client.api_bindings import ConnectorType

from tools.connector_constructor import ConnectorConstructor

LOGGER = logging.getLogger(__name__)


def make_connectors_client() -> Mock:
    connector_config = Mock()
    connector_config.connector_type = ConnectorType.SHIELD
    client = Mock()
    client.get_sensitive_connector.return_value = connector_config
    return client


def shield_connector_patch() -> object:
    # a distinct object per construction, so identity assertions are meaningful
    return patch(
        "tools.connector_constructor.ShieldConnector",
        side_effect=lambda *args, **kwargs: Mock(),
    )


def test_connector_cached_per_constructor() -> None:
    client = make_connectors_client()
    constructor = ConnectorConstructor(client, LOGGER)

    with shield_connector_patch():
        first = constructor.get_connector_from_spec("c1")
        second = constructor.get_connector_from_spec("c1")

    assert first is second
    client.get_sensitive_connector.assert_called_once_with("c1")


def test_connector_cache_not_shared_between_constructors() -> None:
    client = make_connectors_client()

    with shield_connector_patch():
        first = ConnectorConstructor(client, LOGGER).get_connector_from_spec("c1")
        second = ConnectorConstructor(client, LOGGER).get_connector_from_spec("c1")

    assert first is not second
    assert client.get_sensitive_connector.call_count == 2


def test_different_connector_ids_not_cached_together() -> None:
    client = make_connectors_client()
    constructor = ConnectorConstructor(client, LOGGER)

    with shield_connector_patch():
        first = constructor.get_connector_from_spec("c1")
        second = constructor.get_connector_from_spec("c2")

    assert first is not second
    assert client.get_sensitive_connector.call_count == 2
