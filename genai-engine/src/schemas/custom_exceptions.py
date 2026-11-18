from fastapi import HTTPException, status

from utils import constants


class BadCredentialsException(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bad credentials",
        )


class PermissionDeniedException(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )


class RequiresAuthenticationException(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Requires authentication",
        )


class UnableCredentialsException(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to verify credentials",
        )


class AlreadyValidatedException(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=constants.ERROR_CANNOT_VALIDATE_INFERENCE_TWICE,
        )


class GenaiEngineLLMException(Exception):
    def __init__(self, message: str):
        super().__init__(message)

    def get_message(self) -> str:
        return str(self.args[0])


class LLMTokensPerPeriodRateLimitException(GenaiEngineLLMException):
    def __init__(
        self,
        message: str = constants.ERROR_TOKEN_LIMIT_EXCEEDED,
    ):
        super().__init__(message)


class LLMMaxRequestTokensException(GenaiEngineLLMException):
    def __init__(self, message: str):
        super().__init__(message)


class LLMContentFilterException(GenaiEngineLLMException):
    def __init__(
        self,
        message: str = "GenAI Engine was unable to evaluate due to an upstream content policy",
    ):
        super().__init__(message)


class LLMExecutionException(GenaiEngineLLMException):
    def __init__(self, message: str):
        super().__init__(message)


class DefaultModelProviderNotSetException(HTTPException):
    """A call asked for the default model provider, but none is set.

    A distinct type so callers can tell "no default configured" apart from a failed
    LLM call, e.g. to report an insight as skipped instead of failed."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No default model provider is set. Set one on the Model Providers "
                "page: it is used wherever no model is named."
            ),
        )
