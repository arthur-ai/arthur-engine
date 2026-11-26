"""A Microsoft Azure source's credential: a service principal, or the engine's own.

Shared by every connector that calls an Azure API with an Entra token -- AI Foundry and
API Management -- so the one careful way of loading a customer's principal is written
once.

A source's `tenant_id`, `client_id` (source fields, not secrets) and `client_secret` (a
secret) are a Microsoft Entra service principal, used through `ClientSecretCredential`.
All three or none: a partial set is the source's to fix. A source with none uses
`DefaultAzureCredential` -- the engine's managed identity, workload identity, or a
developer's `az login` -- only where the engine opts in, through an environment variable
each vendor names for itself; otherwise it fails naming the fields, rather than quietly
scanning as whatever identity the engine pod happens to run under.

A REFUSED CREDENTIAL IS 401, WHATEVER THE WIRE SAID. azure-identity raises
`ClientAuthenticationError` from the token endpoint, whose status is Entra's (often 400
`invalid_client`) or absent when no credential in the default chain was available.
Neither is the API's answer, and both mean the source's identity could not sign in. The
attribute is set on the SDK's exception and that same exception is re-raised, never
wrapped, as the other cloud connectors do.
"""

import os
from contextlib import contextmanager
from typing import Iterator, Mapping, Optional

from arthur_common.models.connectors import (
    AZURE_CONNECTOR_CLIENT_ID_FIELD,
    AZURE_CONNECTOR_CLIENT_SECRET_FIELD,
    AZURE_CONNECTOR_TENANT_ID_FIELD,
)
from azure.core.credentials import TokenCredential
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import ClientSecretCredential, DefaultAzureCredential

from job_executors.discovery_scan import DiscoveryConfigurationError

TENANT_ID_FIELD = AZURE_CONNECTOR_TENANT_ID_FIELD
CLIENT_ID_FIELD = AZURE_CONNECTOR_CLIENT_ID_FIELD
CLIENT_SECRET_FIELD = AZURE_CONNECTOR_CLIENT_SECRET_FIELD

SENSITIVE_FIELDS: frozenset[str] = frozenset({CLIENT_SECRET_FIELD})

_TRUE = frozenset({"1", "true", "yes"})


def default_credential_allowed(env_var: str) -> bool:
    """Whether the engine operator opted in to DefaultAzureCredential."""
    return os.getenv(env_var, "").strip().lower() in _TRUE


def service_principal_credential(
    tenant_id: Optional[str],
    client_id: Optional[str],
    credentials: Mapping[str, Optional[str]],
    *,
    source: str,
    allow_default_env_var: str,
) -> TokenCredential:
    """The source's service principal, or DefaultAzureCredential where the engine opts in.

    `source` names the source in what is raised, e.g. "Azure AI Foundry source". The
    secret is never part of what is raised: a missing one is named by its field.
    """
    secret = (credentials.get(CLIENT_SECRET_FIELD) or "").strip()
    given = {
        TENANT_ID_FIELD: tenant_id,
        CLIENT_ID_FIELD: client_id,
        CLIENT_SECRET_FIELD: secret or None,
    }
    missing = [field for field, value in given.items() if not value]
    if not missing:
        try:
            return ClientSecretCredential(
                tenant_id=tenant_id or "",
                client_id=client_id or "",
                client_secret=secret,
            )
        except ValueError as e:
            # azure-identity validates the tenant id's characters and names only that;
            # the chained exception is dropped in case a later version says more.
            raise DiscoveryConfigurationError(
                f"{source}'s service principal could not be loaded: {e}",
            ) from None
    if len(missing) < len(given):
        raise DiscoveryConfigurationError(
            f"{source} sets some of a service principal but not "
            f"{', '.join(repr(f) for f in missing)}. Set all of "
            f"'{TENANT_ID_FIELD}', '{CLIENT_ID_FIELD}' and '{CLIENT_SECRET_FIELD}', or "
            f"none of them.",
        )
    if default_credential_allowed(allow_default_env_var):
        return DefaultAzureCredential()
    raise DiscoveryConfigurationError(
        f"{source} has no service principal. Set '{TENANT_ID_FIELD}', "
        f"'{CLIENT_ID_FIELD}' and '{CLIENT_SECRET_FIELD}' on the source, or set "
        f"{allow_default_env_var}=true on this engine to use its "
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
    marked. Used around a scan's calls.
    """
    try:
        yield
    except ClientAuthenticationError as e:
        mark_refused_credential(e)
        raise
