class ServiceError(Exception):
    """Domain error mapped to an HTTP response by the app exception handler."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class Unauthorized(ServiceError):
    def __init__(self, message: str = "Sign in to continue.") -> None:
        super().__init__(message, 401)


class Forbidden(ServiceError):
    def __init__(self, message: str = "You do not have access to that record.") -> None:
        super().__init__(message, 403)


class NotFound(ServiceError):
    def __init__(self, message: str = "That record was not found.") -> None:
        super().__init__(message, 404)


class Conflict(ServiceError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 409)


class RateLimited(ServiceError):
    def __init__(self, message: str, retry_after: int) -> None:
        super().__init__(message, 429)
        self.retry_after = retry_after
