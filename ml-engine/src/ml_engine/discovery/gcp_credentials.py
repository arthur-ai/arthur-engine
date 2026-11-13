"""A Google Cloud source's credentials: a pasted service account key, or the engine's own.

Shared by every connector that calls a Google API -- Vertex AI Agent Engine and Compute
Engine -- so the one careful way of loading a customer's key is written once.

THE KEY IS LOADED AS A SERVICE ACCOUNT AND NOTHING ELSE. `service_account.Credentials.
from_service_account_info`, deliberately not `google.auth.load_credentials_from_dict`,
which also accepts external-account configs that can name an executable or a file on
this engine's disk.

A KEYLESS SOURCE USES THE ENGINE'S IDENTITY ONLY WHERE THE ENGINE OPTS IN. Each vendor
names its own environment variable for that. With it unset a keyless source fails with a
reason naming the field, rather than quietly scanning as whatever identity the engine
pod happens to run under.

A REFUSED CREDENTIAL IS 401, WHATEVER THE WIRE SAID. A revoked or deleted key, or ADC
whose user login has lapsed, fails before the API is ever asked: google-auth cannot mint
a token, and raises `RefreshError` -- usually off a 400 `invalid_grant` from Google's
token endpoint, which `failure_code` would not know to read as an authentication failure.
Only a non-retryable one is: google-auth marks the token endpoint's own 5xx and
`temporarily_unavailable` answers retryable, and those are Google's outage, not the
source's key. Nor is one raised from a `TransportError`: google-auth wraps a metadata
server it could not reach that way, without marking it retryable, and that is the
network's failure, not a refused credential.
"""

import json
import os
import re
from typing import Mapping, Optional, Sequence

from google.auth.credentials import Credentials
from google.auth.exceptions import RefreshError, TransportError
from google.oauth2 import service_account

from job_executors.discovery_scan import DiscoveryConfigurationError

SERVICE_ACCOUNT_KEY_FIELD = "service_account_key"

# A project id, optionally domain-scoped (`example.com:my-project`). Checked by every
# connector that takes one, because it is a path segment in every call.
GCP_PROJECT_ID = re.compile(r"^(?:[a-z0-9.-]+:)?[a-z][a-z0-9-]{4,28}[a-z0-9]$")


def adc_allowed(env_var: str) -> bool:
    """Whether the engine operator opted in to Application Default Credentials."""
    return os.getenv(env_var, "").strip().lower() in {"1", "true", "yes"}


def service_account_credentials(
    credentials: Mapping[str, Optional[str]],
    *,
    source: str,
    allow_adc_env_var: str,
    scopes: Sequence[str],
) -> Optional[Credentials]:
    """The source's service account, or None to use Application Default Credentials.

    `source` names the source in what is raised, e.g. "Vertex AI source". None is
    returned only when the engine has opted in to ADC through `allow_adc_env_var`; a
    keyless source on an engine that has not raises instead.

    A key that does not parse is reported without its content. The job logger scrubs the
    whole key string by exact match, but a JSON error quotes a fragment of the document,
    and a fragment is not what the scrub set holds.
    """
    field = SERVICE_ACCOUNT_KEY_FIELD
    raw = (credentials.get(field) or "").strip()
    if not raw:
        if adc_allowed(allow_adc_env_var):
            return None
        raise DiscoveryConfigurationError(
            f"{source} has no '{field}'. Paste a service account JSON key into the "
            f"source, or set {allow_adc_env_var}=true on this engine to use its "
            f"Application Default Credentials.",
        )

    try:
        info = json.loads(raw)
    except json.JSONDecodeError as e:
        raise DiscoveryConfigurationError(
            f"{source}'s '{field}' is not valid JSON (line {e.lineno}, column "
            f"{e.colno}). Paste the whole key file.",
        ) from None
    if not isinstance(info, dict) or info.get("type") != "service_account":
        raise DiscoveryConfigurationError(
            f"{source}'s '{field}' is not a service account key: expected a JSON "
            f'object with "type": "service_account".',
        )
    try:
        loaded: Credentials = service_account.Credentials.from_service_account_info(  # type: ignore[no-untyped-call]
            info,
            scopes=list(scopes),
        )
        return loaded
    except ValueError as e:
        # google-auth names the missing field, never the key material, so its message
        # is safe to carry; the chained exception is dropped in case a later version
        # is less careful.
        raise DiscoveryConfigurationError(
            f"{source}'s '{field}' could not be loaded: {e}",
        ) from None


def mark_refused_credential(e: RefreshError) -> None:
    """Set `status_code` 401 on a RefreshError that means the credential was refused.

    The attribute is set on google-auth's own exception, which the caller re-raises
    unwrapped; see the module docstring for which failures count.
    """
    if not e.retryable and not isinstance(e.__cause__, TransportError):
        setattr(e, "status_code", 401)
