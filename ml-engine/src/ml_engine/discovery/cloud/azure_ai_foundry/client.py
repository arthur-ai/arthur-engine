"""What a Foundry source's scan needs: settings, credential, client.

ONE PROJECT PER SOURCE. A source names a Foundry project by its endpoint,
`https://<resource>.services.ai.azure.com/api/projects/<project>`, which is what the
Foundry portal shows on the project's overview page and what `AIProjectClient` takes.
The resource (the Foundry account) and the project are read back out of it for the
record's address, so the endpoint is the one thing a person types.

CREDENTIALS. A source's `tenant_id`, `client_id` (source fields, not secrets) and
`client_secret` (a secret) are a Microsoft Entra service principal, used through
`ClientSecretCredential`. All three or none: a partial set is the source's to fix. A
source with none uses `DefaultAzureCredential` -- the engine's managed identity, workload
identity, or a developer's `az login` -- only when the engine opts in with
`ALLOW_DEFAULT_CREDENTIAL_ENV_VAR`; otherwise it fails naming the fields, rather than
quietly scanning as whatever identity the engine pod happens to run under. The SDK asks
the credential for the `https://ai.azure.com/.default` scope itself.

WHAT AZURE ANSWERED. azure-core's `HttpResponseError` already carries the HTTP status
on `status_code`, which is the attribute `discovery_scan.failure_code` reads, so a
project the principal cannot read is `permission_denied` with no translation. A refused
credential is the exception: azure-identity raises `ClientAuthenticationError` from the
token endpoint, whose status is Entra's (often 400 `invalid_client`) or absent when no
credential in the default chain was available. Neither is Foundry's answer, and both
mean the source's identity could not sign in, so it is marked 401 whatever the wire said.
The attribute is set on the SDK's exception and that same exception is re-raised, never
wrapped, as the other cloud connectors do.
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    ContextManager,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Protocol,
)
from urllib.parse import urlsplit

from arthur_common.models.connectors import (
    AZURE_CONNECTOR_CLIENT_ID_FIELD,
    AZURE_CONNECTOR_CLIENT_SECRET_FIELD,
    AZURE_CONNECTOR_TENANT_ID_FIELD,
)
from azure.ai.projects import AIProjectClient
from azure.core.credentials import TokenCredential
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import ClientSecretCredential, DefaultAzureCredential

from job_executors.discovery_scan import DiscoveryConfigurationError

PROJECT_ENDPOINT_FIELD = "project_endpoint"
TENANT_ID_FIELD = AZURE_CONNECTOR_TENANT_ID_FIELD
CLIENT_ID_FIELD = AZURE_CONNECTOR_CLIENT_ID_FIELD
CLIENT_SECRET_FIELD = AZURE_CONNECTOR_CLIENT_SECRET_FIELD

SENSITIVE_FIELDS: frozenset[str] = frozenset({CLIENT_SECRET_FIELD})

# Opt-in for DefaultAzureCredential when a source has no service principal. Off unless
# set to a true value; see the module docstring.
ALLOW_DEFAULT_CREDENTIAL_ENV_VAR = (
    "ARTHUR_ENGINE_AZURE_AI_FOUNDRY_ALLOW_DEFAULT_CREDENTIAL"
)

_SOURCE = "Azure AI Foundry source"
_TRUE = frozenset({"1", "true", "yes"})


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

    A seam so tests hand in fakes instead of patching the SDK. `list` yields
    `AgentDetails`.
    """

    def list(self) -> Iterable[Any]: ...


# (settings, credential) -> the project's agent operations, closed on exit.
AgentsFactory = Callable[
    [FoundrySettings, TokenCredential], ContextManager[FoundryAgents]
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

    The host is not checked against `services.ai.azure.com`, so a sovereign cloud's
    endpoint works; the path is, because the project name is read from it.
    """
    parts = urlsplit(raw.strip())
    segments = [s for s in parts.path.split("/") if s]
    host = (parts.hostname or "").lower()
    if (
        parts.scheme.lower() != "https"
        or not host
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
    netloc = host if parts.port is None else f"{host}:{parts.port}"
    project = segments[2]
    return f"https://{netloc}/api/projects/{project}", host.split(".")[0], project


def default_credential_allowed() -> bool:
    """Whether the engine operator opted in to DefaultAzureCredential."""
    return os.getenv(ALLOW_DEFAULT_CREDENTIAL_ENV_VAR, "").strip().lower() in _TRUE


def credential_from(
    settings: FoundrySettings,
    credentials: Mapping[str, Optional[str]],
) -> TokenCredential:
    """The source's service principal, or DefaultAzureCredential where the engine opts in.

    The secret is never part of what is raised: a missing one is named by its field.
    """
    secret = (credentials.get(CLIENT_SECRET_FIELD) or "").strip()
    given = {
        TENANT_ID_FIELD: settings.tenant_id,
        CLIENT_ID_FIELD: settings.client_id,
        CLIENT_SECRET_FIELD: secret or None,
    }
    missing = [field for field, value in given.items() if not value]
    if not missing:
        try:
            return ClientSecretCredential(
                tenant_id=settings.tenant_id or "",
                client_id=settings.client_id or "",
                client_secret=secret,
            )
        except ValueError as e:
            # azure-identity validates the tenant id's characters and names only that;
            # the chained exception is dropped in case a later version says more.
            raise DiscoveryConfigurationError(
                f"{_SOURCE}'s service principal could not be loaded: {e}",
            ) from None
    if len(missing) < len(given):
        raise DiscoveryConfigurationError(
            f"{_SOURCE} sets some of a service principal but not "
            f"{', '.join(repr(f) for f in missing)}. Set all of "
            f"'{TENANT_ID_FIELD}', '{CLIENT_ID_FIELD}' and '{CLIENT_SECRET_FIELD}', or "
            f"none of them.",
        )
    if default_credential_allowed():
        return DefaultAzureCredential()
    raise DiscoveryConfigurationError(
        f"{_SOURCE} has no service principal. Set '{TENANT_ID_FIELD}', "
        f"'{CLIENT_ID_FIELD}' and '{CLIENT_SECRET_FIELD}' on the source, or set "
        f"{ALLOW_DEFAULT_CREDENTIAL_ENV_VAR}=true on this engine to use its "
        f"DefaultAzureCredential.",
    )


def describe_credential(credential: TokenCredential) -> str:
    """What the job log says the scan signs in as, without anything secret."""
    if isinstance(credential, ClientSecretCredential):
        return "the source's service principal"
    return "the engine's DefaultAzureCredential"


def mark_refused_credential(e: ClientAuthenticationError) -> None:
    """Set `status_code` 401 on a credential Entra refused; see the module docstring."""
    setattr(e, "status_code", 401)


@contextmanager
def vendor_status() -> Iterator[None]:
    """Re-raise what the SDK raised with a status `failure_code` can read.

    `HttpResponseError` keeps its own `status_code`; only a refused credential is
    marked. Used around the scan's listing.
    """
    try:
        yield
    except ClientAuthenticationError as e:
        mark_refused_credential(e)
        raise
