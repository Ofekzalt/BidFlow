from auth.constants.auth_constants import (
    ERROR_EMAIL_ALREADY_REGISTERED,
    ERROR_INVALID_CREDENTIALS,
)


class AuthError(Exception):
    status_code: int
    detail: str

    def __init__(self, detail: str, status_code: int) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class EmailAlreadyRegisteredError(AuthError):
    def __init__(self) -> None:
        super().__init__(ERROR_EMAIL_ALREADY_REGISTERED, 409)


class InvalidCredentialsError(AuthError):
    def __init__(self) -> None:
        super().__init__(ERROR_INVALID_CREDENTIALS, 401)
