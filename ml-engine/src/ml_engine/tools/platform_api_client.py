from arthur_client.api_bindings import ApiClient
from arthur_client.auth import (
    ArthurClientCredentialsAPISession,
    ArthurOAuthSessionAPIConfiguration,
    ArthurOIDCMetadata,
)

from config import Config
from tools.engine_version import set_engine_version_header


def build_platform_api_client() -> ApiClient:
    """Authenticated client for the Arthur platform, announcing this engine's version."""
    ssl_verify = Config.get_bool(
        "ARTHUR_API_HOST_SSL_VERIFY",
        True,
        fallback_keys=["KEYCLOAK_SSL_VERIFY"],
    )
    sess = ArthurClientCredentialsAPISession(
        client_id=Config.settings.ARTHUR_CLIENT_ID,
        client_secret=Config.settings.ARTHUR_CLIENT_SECRET,
        metadata=ArthurOIDCMetadata(
            arthur_host=Config.settings.ARTHUR_API_HOST,
            verify_ssl=ssl_verify,
        ),
        verify=ssl_verify,
    )
    return set_engine_version_header(
        ApiClient(
            configuration=ArthurOAuthSessionAPIConfiguration(
                session=sess,
                verify_ssl=ssl_verify,
            ),
        ),
    )
