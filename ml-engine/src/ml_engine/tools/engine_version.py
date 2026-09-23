from importlib.metadata import PackageNotFoundError, version

from arthur_client.api_bindings import ApiClient

# The control plane reads this to tell whether an engine understands
# consolidated task datasets. Engines from before consolidation send nothing,
# so the control plane treats an absent header as "legacy" and narrows what it
# returns. Sending it here is what lets a data plane upgrade on its own
# schedule without any coordinated change on the platform side.
ENGINE_VERSION_HEADER = "X-Arthur-Engine-Version"


def engine_version() -> str:
    try:
        return version("ml-engine")
    except PackageNotFoundError:
        return "unknown"


def set_engine_version_header(client: ApiClient) -> ApiClient:
    """Announce this engine's version on every request the client makes."""
    client.set_default_header(ENGINE_VERSION_HEADER, engine_version())
    return client
