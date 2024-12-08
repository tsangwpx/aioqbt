"""
Exceptions raised in :mod:`aioqbt`.

"""

import logging
import sys
from typing import Optional

import aiohttp
from typing_extensions import Self


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
    Base class of API errors.
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
    ) -> Self:
        """Create an exception instance based on a response."""

        return cls(
            message=message or str(resp.reason),
            status=resp.status,
            resp=resp,
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}(status={self.status!r}, message={self.message!r})"

    def __str__(self) -> str:
        return repr(self)


class LoginError(APIError):
    """
    Login has failed.

    This is raised by :meth:`.AuthAPI.login` and HTTP status is 200.
    """


class AddTorrentError(APIError):
    """
    No **new** torrents were added.

    This is raised by :meth:`.TorrentsAPI.add` and HTTP status is 200.
    """


class BadRequestError(APIError):
    """
    Bad request.

    The error is usually raised because of missing or invalid parameters.
    This may be caused by empty value sometimes.

    HTTP status is usually 400.
    """


class ForbiddenError(APIError):
    """
    Forbidden.

    The request to resources is explicitly denied due to permission.

    HTTP status is usually 403.
    """


class NotFoundError(APIError):
    """
    Not found.

    It is likely that the API endpoint is misspelled or qBittorrent need an update.

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


def _add_note(
    ex: Optional[BaseException],
    note: str,
    *,
    logger: Optional[logging.Logger] = None,
    log_level: Optional[int] = None,
) -> None:
    """
    Add a note to exception if Python version >= 3.11 or record with logger
    """

    if sys.version_info >= (3, 11):
        ex.add_note(note)
        return

    # fallback to logging
    if logger is None:
        logger = logging.getLogger(f"{__name__}.note")

    if log_level is None:
        log_level = logging.WARNING

    logger.log(log_level, note, exc_info=ex)
