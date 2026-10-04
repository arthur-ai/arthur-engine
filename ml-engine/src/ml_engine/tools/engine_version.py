import logging
from functools import cache
from pathlib import Path
from typing import Optional

from arthur_client.api_bindings import ApiClient
from arthur_common.models.constants import ENGINE_VERSION_HEADER

logger = logging.getLogger(__name__)

# Written by version-workflow.yml on every bump. Lives inside the package so the
# image's `COPY src/ml_engine` carries it: the image never installs the project
# itself, so package metadata is not available there.
VERSION_FILE = Path(__file__).parent.parent / "version"


@cache
def engine_version() -> Optional[str]:
    try:
        return VERSION_FILE.read_text().strip() or None
    except OSError:
        logger.warning(
            "Can't read engine version from %s; platform will treat this engine as legacy",
            VERSION_FILE,
        )
        return None


def set_engine_version_header(client: ApiClient) -> ApiClient:
    """Announce this engine's version on every request the client makes.

    Sends nothing when the version is unknown, so the engine lands in the
    control plane's defined legacy bucket rather than an unparseable value.
    """
    version = engine_version()
    if version is not None:
        client.set_default_header(ENGINE_VERSION_HEADER, version)
    return client
