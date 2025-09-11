from fastapi import HTTPException, status

from utils import constants


class BadCredentialsException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bad credentials",
        )


class PermissionDeniedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )


class RequiresAuthenticationException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Requires authentication",
        )


class UnableCredentialsException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to verify credentials",
        )


class AlreadyValidatedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=constants.ERROR_CANNOT_VALIDATE_INFERENCE_TWICE,
        )


class GenaiEngineLLMException(Exception):
    def __init__(self, message: str):
        super().__init__(message)

    def get_message(self) -> str:
        return self.args[0]


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
