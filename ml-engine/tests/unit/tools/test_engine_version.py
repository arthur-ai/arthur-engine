from arthur_client.api_bindings import ApiClient
from tools.engine_version import (
    ENGINE_VERSION_HEADER,
    engine_version,
    set_engine_version_header,
)


def test_engine_version_is_resolved() -> None:
    # Resolved from package metadata, so it tracks pyproject without a second
    # place to bump. The control plane only checks presence, but a real value
    # keeps the header useful for debugging.
    assert engine_version() != "unknown"


def test_set_engine_version_header() -> None:
    # The control plane treats an absent header as an engine predating dataset
    # consolidation, so every client this engine builds must announce itself.
    client = set_engine_version_header(ApiClient())
    assert client.default_headers[ENGINE_VERSION_HEADER] == engine_version()
