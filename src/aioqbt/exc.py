"""
Exceptions raised in :mod:`aioqbt`.

"""

from typing import Optional

import aiohttp


class AQError(Exception):
    """
    Generic error class.
    """


class MapperError(AQError):
    """
    Raised when mapper operations failed.
    """


class VersionError(AQError):
    """
    Version check failed.
    """


class APIError(AQError):
    """
    Errors of unintended API response.

    """

    message: str
    """Error message or HTTP reason phrase"""

    status: int
    """HTTP status"""

    resp: Optional[aiohttp.ClientResponse]
    """The closed response object"""

    def __init__(
        self,
        message: str = "",
        status: int = 0,
        resp: Optional[aiohttp.ClientResponse] = None,
    ):
        self.message = message
        self.status = status
        self.resp = resp

    @classmethod
    def from_response(
        cls,
        resp: aiohttp.ClientResponse,
        message: str = "",
    ):
        """Create an exception instance based on a response."""

        return cls(
            message=message or str(resp.reason),
            status=resp.status,
            resp=resp,
        )

    def __repr__(self):
        return f"{type(self).__name__}(status={self.status!r}, message={self.message!r})"

    def __str__(self):
        return repr(self)


class LoginError(APIError):
    """
    Login has failed.

    This is raised by :meth:`.AuthAPI.login` and HTTP status is 200.
    """


class AddTorrentError(APIError):
    """
    No URLs nor torrents were added.

    This is raised by :meth:`.TorrentsAPI.add` and HTTP status is 200.
    """


class BadRequestError(APIError):
    """
    Bad request.

    HTTP status is usually 400.

    The error is usually raised because of missing or invalid parameters.
    This may be caused by empty value sometimes.
    """


class ForbiddenError(APIError):
    """
    Forbidden.

    HTTP status is usually 403.

    The request to resources is explicitly denied due to permission.
    """


class NotFoundError(APIError):
    """
    Not found.

    HTTP status is usually 404.
    """


class ConflictError(APIError):
    """
    Conflict.

    HTTP status is usually 409.
    """


class UnsupportedMediaTypeError(APIError):
    """
    Unsupported media type.

    HTTP status is usually 415.
    """


# lookup error class by status
# {status: exc_class}
_ERROR_TABLE = {
    400: BadRequestError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    415: UnsupportedMediaTypeError,
}
