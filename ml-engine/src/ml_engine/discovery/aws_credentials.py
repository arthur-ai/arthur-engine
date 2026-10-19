"""An AWS source's credentials: an access key, a role assumed with one, or the engine's own.

The field names are arthur-common's AWS connector fields, the ones the S3 connector reads,
so a person who has configured one AWS source has configured them all. The key pair is
sensitive; `role_arn` and `external_id` are not, so a job log can say which role was
refused.

THE ENGINE'S OWN IDENTITY ONLY WHERE THE ENGINE OPTS IN, whether it is used directly or to
assume `role_arn`. Each vendor names its own environment variable for that, as Google's
sources do. A role is chosen by whoever configures the source, and roles in the engine's
own account may trust the engine's identity; without the opt-in a source could have the
engine assume one of them. With it unset, a source with no key fails with a reason naming
the fields.

A ROLE IS ASSUMED WHEN FIRST USED AND REFRESHED BEFORE IT EXPIRES. A scan of a large
fleet makes a call per machine and can outlast the one-hour session, so the assumed
credentials are refreshable rather than fetched once.
"""

import os
from typing import Mapping, Optional

import boto3
import botocore.session
from arthur_common.models.connectors import (
    AWS_CONNECTOR_ACCESS_KEY_ID_FIELD,
    AWS_CONNECTOR_EXTERNAL_ID_FIELD,
    AWS_CONNECTOR_ROLE_ARN_FIELD,
    AWS_CONNECTOR_SECRET_ACCESS_KEY_FIELD,
)
from botocore.credentials import (
    AssumeRoleCredentialFetcher,
    CredentialProvider,
    CredentialResolver,
    Credentials,
    DeferredRefreshableCredentials,
)

from job_executors.discovery_scan import DiscoveryConfigurationError

ACCESS_KEY_ID_FIELD = AWS_CONNECTOR_ACCESS_KEY_ID_FIELD
SECRET_ACCESS_KEY_FIELD = AWS_CONNECTOR_SECRET_ACCESS_KEY_FIELD
ROLE_ARN_FIELD = AWS_CONNECTOR_ROLE_ARN_FIELD
EXTERNAL_ID_FIELD = AWS_CONNECTOR_EXTERNAL_ID_FIELD

SENSITIVE_FIELDS = frozenset({ACCESS_KEY_ID_FIELD, SECRET_ACCESS_KEY_FIELD})


def default_credentials_allowed(env_var: str) -> bool:
    """Whether the engine operator opted in to the engine's own AWS credentials."""
    return os.getenv(env_var, "").strip().lower() in {"1", "true", "yes"}


class _AssumeRoleProvider(CredentialProvider):  # type: ignore[misc]
    """The role's credentials, fetched on first use and refreshed before expiry."""

    METHOD = "assume-role"
    CANONICAL_NAME = "arthur-discovery-assume-role"

    def __init__(self, fetcher: AssumeRoleCredentialFetcher) -> None:
        super().__init__()
        self._fetcher = fetcher

    def load(self) -> DeferredRefreshableCredentials:
        return DeferredRefreshableCredentials(
            refresh_using=self._fetcher.fetch_credentials,
            method=self.METHOD,
        )


def aws_session(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
    *,
    source: str,
    allow_default_env_var: str,
    session_name: str,
    region_name: Optional[str] = None,
) -> boto3.Session:
    """A session holding the source's credentials, or raise naming what is missing.

    `source` names the source in what is raised, e.g. "EC2 source". `session_name`
    becomes the assumed role's session name, which the customer's CloudTrail shows.
    `region_name` is where STS is asked for the role: an engine need not have a default
    region of its own, and a session without one cannot always build an STS client.
    """
    key_id = (credentials.get(ACCESS_KEY_ID_FIELD) or "").strip()
    secret = (credentials.get(SECRET_ACCESS_KEY_FIELD) or "").strip()
    role_arn = (source_fields.get(ROLE_ARN_FIELD) or "").strip()
    external_id = (source_fields.get(EXTERNAL_ID_FIELD) or "").strip()

    if bool(key_id) != bool(secret):
        missing = SECRET_ACCESS_KEY_FIELD if key_id else ACCESS_KEY_ID_FIELD
        raise DiscoveryConfigurationError(
            f"{source} has half an access key: '{missing}' is empty. Set both "
            f"'{ACCESS_KEY_ID_FIELD}' and '{SECRET_ACCESS_KEY_FIELD}', or neither.",
        )
    if external_id and not role_arn:
        raise DiscoveryConfigurationError(
            f"{source} sets '{EXTERNAL_ID_FIELD}' without '{ROLE_ARN_FIELD}'. An "
            f"external ID is only sent when assuming a role.",
        )
    if not key_id and not default_credentials_allowed(allow_default_env_var):
        raise DiscoveryConfigurationError(
            f"{source} has no '{ACCESS_KEY_ID_FIELD}' and '{SECRET_ACCESS_KEY_FIELD}'. "
            f"Set them, with '{ROLE_ARN_FIELD}' if the key should assume a role, or set "
            f"{allow_default_env_var}=true on this engine to use its own AWS "
            f"credentials.",
        )

    base = boto3.Session(
        aws_access_key_id=key_id or None,
        aws_secret_access_key=secret or None,
        region_name=region_name,
    )
    if not role_arn:
        return base

    source_credentials: Optional[Credentials] = base.get_credentials()
    if source_credentials is None:
        raise DiscoveryConfigurationError(
            f"{source} has no key to assume '{ROLE_ARN_FIELD}' with, and this engine "
            f"has no AWS credentials of its own to use instead.",
        )
    extra: dict[str, str] = {"RoleSessionName": session_name}
    if external_id:
        extra["ExternalId"] = external_id
    fetcher = AssumeRoleCredentialFetcher(
        client_creator=base._session.create_client,
        source_credentials=source_credentials,
        role_arn=role_arn,
        extra_args=extra,
    )
    assumed = botocore.session.Session()
    assumed.register_component(
        "credential_provider",
        CredentialResolver([_AssumeRoleProvider(fetcher)]),
    )
    return boto3.Session(botocore_session=assumed, region_name=region_name)
