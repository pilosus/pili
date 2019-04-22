from typing import Optional


class RequestError(Exception):
    """
    Basic request error
    """

    status_code = 500

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        origin: Optional[Exception] = None,
        extra: Optional[dict] = None,
    ) -> None:
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code or 500
        self.extra = extra or {}


class ValidationError(RequestError):
    status_code = 400


class UnauthorizedError(RequestError):
    status_code = 401


class ForbiddenError(RequestError):
    status_code = 403
