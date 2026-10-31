import logging
from types import SimpleNamespace

from arthur_client.api_bindings import ConnectorSpec

from acting_user import ACTING_USER, ON_BEHALF_OF_HEADER, acting_user_of
from connectors.shield_connector import EngineInternalConnector, ShieldConnector
from tests.unit.connectors.test_shield_connector import (
    MOCK_SHIELD_HOST,
    mock_engine_internal_connector_spec,
    mock_shield_connector_spec,
)

logger = logging.getLogger("job_logger")


def _job(user):  # type: ignore[no-untyped-def]
    return SimpleNamespace(triggered_by_user=user)


def test_acting_user_prefers_email_then_id() -> None:
    assert acting_user_of(_job(SimpleNamespace(email="a@x.com", id="u1"))) == "a@x.com"
    assert acting_user_of(_job(SimpleNamespace(email=None, id="u1"))) == "u1"
    assert acting_user_of(_job(None)) is None


def test_internal_connector_names_the_acting_user() -> None:
    token = ACTING_USER.set("alice@example.com")
    try:
        conn = EngineInternalConnector(
            ConnectorSpec.model_validate(mock_engine_internal_connector_spec()),
            logger,
        )
    finally:
        ACTING_USER.reset(token)
    assert (
        conn._genai_client.default_headers[ON_BEHALF_OF_HEADER] == "alice@example.com"
    )


def test_internal_connector_sends_nothing_for_scheduled_jobs() -> None:
    conn = EngineInternalConnector(
        ConnectorSpec.model_validate(mock_engine_internal_connector_spec()),
        logger,
    )
    assert ON_BEHALF_OF_HEADER not in conn._genai_client.default_headers


def test_customer_engine_connector_never_sends_the_header() -> None:
    """A customer-configured engine is reached with the customer's own key, which
    the engine would not honour the header for; do not send the user's email."""
    token = ACTING_USER.set("alice@example.com")
    try:
        conn = ShieldConnector(
            ConnectorSpec.model_validate(mock_shield_connector_spec(MOCK_SHIELD_HOST)),
            logger,
        )
    finally:
        ACTING_USER.reset(token)
    assert ON_BEHALF_OF_HEADER not in conn._genai_client.default_headers
