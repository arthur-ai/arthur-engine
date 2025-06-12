from typing import Union

from aiobotocore.credentials import (
    AioAssumeRoleCredentialFetcher,
    AioCredentialResolver,
    AioDeferredRefreshableCredentials,
)
from aiobotocore.session import AioSession, ClientCreatorContext, get_session
from botocore.credentials import CredentialProvider, Credentials


class AioAssumeRoleCredentialProvider(CredentialProvider):  # type: ignore
    METHOD = "assume-role"
    CANONICAL_NAME = "aio-assume-role-provider"

    def __init__(
        self,
        client_creator: ClientCreatorContext,
        source_credentials: Credentials,
        role_arn: str,
        duration: int = 3600,
        external_id: str | None = None,
        session_name: str | None = None,
    ) -> None:
        super().__init__()
        args: dict[str, Union[str, int]] = {"DurationSeconds": duration}
        if external_id is not None:
            args["ExternalId"] = external_id
        if session_name is not None:
            args["RoleSessionName"] = session_name

        self._fetcher = AioAssumeRoleCredentialFetcher(
            client_creator=client_creator,
            source_credentials=source_credentials,
            role_arn=role_arn,
            extra_args=args,
        )

    async def load(self) -> AioDeferredRefreshableCredentials:
        return AioDeferredRefreshableCredentials(
            refresh_using=self._fetcher.fetch_credentials,
            method=self.METHOD,
        )


async def assume_role(
    session: AioSession,
    role_arn: str,
    duration: int = 3600,
    external_id: str | None = None,
    session_name: str | None = None,
) -> AioSession:
    """Assume role for an AioSession session, with automatic credential refresh;
    See https://github.com/boto/botocore/issues/761
    """
    # create auto refresh credential provider
    client_creator = session.create_client
    source_credentials = await session.get_credentials()
    provider = AioAssumeRoleCredentialProvider(
        client_creator=client_creator,
        source_credentials=source_credentials,
        role_arn=role_arn,
        duration=duration,
        external_id=external_id,
        session_name=session_name,
    )
    # create child session which will assume the role
    child = get_session()
    child.register_component("credential_provider", AioCredentialResolver([provider]))
    return child
