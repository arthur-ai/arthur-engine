"""What a Foundry source's scan needs: settings, credential, client.

ONE PROJECT PER SOURCE. A source names a Foundry project by its endpoint,
`https://<resource>.services.ai.azure.com/api/projects/<project>`, which is what the
Foundry portal shows on the project's overview page and what `AIProjectClient` takes.
The resource (the Foundry account) and the project are read back out of it for the
record's address, so the endpoint is the one thing a person types.

PUBLIC AZURE ONLY. The host must be `<resource>.services.ai.azure.com`. The scan hands
the endpoint a bearer token, for the engine's own identity when the default credential
is allowed, so a source must not be able to point it at a host of its choosing. The SDK
also asks for the public cloud's `https://ai.azure.com/.default` scope, which a sovereign
cloud's Foundry would not accept; supporting one means adding its domain, its scope and
its Entra authority together.

CREDENTIALS are `discovery.azure_credentials`', under this vendor's own opt-in for the
engine's identity. The SDK asks the credential for the `https://ai.azure.com/.default`
scope itself.

WHAT AZURE ANSWERED. azure-core's `HttpResponseError` already carries the HTTP status
on `status_code`, which is the attribute `discovery_scan.failure_code` reads, so a
project the principal cannot read is `permission_denied` with no translation. A refused
credential is marked 401 by `discovery.azure_credentials`.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    ContextManager,
    Iterator,
    Mapping,
    Optional,
    Protocol,
)
from urllib.parse import urlsplit

from azure.ai.projects import AIProjectClient
from azure.core.credentials import TokenCredential
from azure.core.paging import ItemPaged

from discovery import azure_credentials
from discovery.azure_credentials import (
    CLIENT_ID_FIELD,
    CLIENT_SECRET_FIELD,
    SENSITIVE_FIELDS,
    TENANT_ID_FIELD,
    describe_credential,
    mark_refused_credential,
    vendor_status,
)
from job_executors.discovery_scan import DiscoveryConfigurationError

PROJECT_ENDPOINT_FIELD = "project_endpoint"

# Opt-in for DefaultAzureCredential when a source has no service principal. Off unless
# set to a true value; see the module docstring.
ALLOW_DEFAULT_CREDENTIAL_ENV_VAR = (
    "ARTHUR_ENGINE_AZURE_AI_FOUNDRY_ALLOW_DEFAULT_CREDENTIAL"
)

_SOURCE = "Azure AI Foundry source"
_ENDPOINT_DOMAIN = ".services.ai.azure.com"


@dataclass(frozen=True)
class FoundrySettings:
    # Normalised: lower-case scheme and host, no trailing slash. The external id is
    # built from it, so two spellings of one endpoint must not be two agents.
    project_endpoint: str
    # The Foundry resource (account) name: the first label of the endpoint's host.
    resource_name: str
    project_name: str
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None


class FoundryAgents(Protocol):
    """The part of `AIProjectClient.agents` (azure-ai-projects 2.4) this package calls.

    A seam so tests hand in fakes instead of patching the SDK. `list` pages
    `AgentDetails`; the scan reads it page by page to watch the continuation token.
    """

    def list(self) -> ItemPaged[Any]: ...


# (settings, credential) -> the project's agent operations, closed on exit.
AgentsFactory = Callable[
    [FoundrySettings, TokenCredential],
    ContextManager[FoundryAgents],
]


@contextmanager
def project_agents(
    settings: FoundrySettings,
    credential: TokenCredential,
) -> Iterator[FoundryAgents]:
    """The SDK's agent operations for one project, its HTTP session closed after use."""
    with AIProjectClient(
        endpoint=settings.project_endpoint,
        credential=credential,
    ) as client:
        yield client.agents


def settings_from(source_fields: Mapping[str, str]) -> FoundrySettings:
    """The project endpoint and the principal's ids from the source's non-sensitive fields."""
    raw = (source_fields.get(PROJECT_ENDPOINT_FIELD) or "").strip()
    if not raw:
        raise DiscoveryConfigurationError(
            f"{_SOURCE} is missing required field '{PROJECT_ENDPOINT_FIELD}', the "
            f"project endpoint shown on the Foundry project's overview page "
            f"(https://<resource>.services.ai.azure.com/api/projects/<project>). It is "
            f"a source field, not a secret.",
        )
    endpoint, resource_name, project_name = parse_project_endpoint(raw)
    return FoundrySettings(
        project_endpoint=endpoint,
        resource_name=resource_name,
        project_name=project_name,
        tenant_id=(source_fields.get(TENANT_ID_FIELD) or "").strip() or None,
        client_id=(source_fields.get(CLIENT_ID_FIELD) or "").strip() or None,
    )


def parse_project_endpoint(raw: str) -> tuple[str, str, str]:
    """(normalised endpoint, resource name, project name), or DiscoveryConfigurationError.

    The host must be a public Azure Foundry resource's; see the module docstring.
    """
    parts = urlsplit(raw.strip())
    segments = [s for s in parts.path.split("/") if s]
    host = (parts.hostname or "").lower()
    resource = host.removesuffix(_ENDPOINT_DOMAIN)
    try:
        port = parts.port
    except ValueError:
        port = -1
    if (
        parts.scheme.lower() != "https"
        or not host.endswith(_ENDPOINT_DOMAIN)
        or not resource
        or "." in resource
        or port not in (None, 443)
        or parts.username is not None
        or parts.query
        or parts.fragment
        or len(segments) != 3
        or segments[0] != "api"
        or segments[1] != "projects"
    ):
        raise DiscoveryConfigurationError(
            f"{_SOURCE}'s '{PROJECT_ENDPOINT_FIELD}' {raw!r} is not a Foundry project "
            f"endpoint: expected https://<resource>.services.ai.azure.com/api/projects/"
            f"<project>.",
        )
    project = segments[2]
    return f"https://{host}/api/projects/{project}", resource, project


def default_credential_allowed() -> bool:
    """Whether the engine operator opted in to DefaultAzureCredential."""
    return azure_credentials.default_credential_allowed(
        ALLOW_DEFAULT_CREDENTIAL_ENV_VAR,
    )


def credential_from(
    settings: FoundrySettings,
    credentials: Mapping[str, Optional[str]],
) -> TokenCredential:
    """The source's service principal, or DefaultAzureCredential where the engine opts in."""
    return azure_credentials.service_principal_credential(
        settings.tenant_id,
        settings.client_id,
        credentials,
        source=_SOURCE,
        allow_default_env_var=ALLOW_DEFAULT_CREDENTIAL_ENV_VAR,
    )


__all__ = [
    "CLIENT_ID_FIELD",
    "CLIENT_SECRET_FIELD",
    "SENSITIVE_FIELDS",
    "TENANT_ID_FIELD",
    "describe_credential",
    "mark_refused_credential",
    "vendor_status",
]
