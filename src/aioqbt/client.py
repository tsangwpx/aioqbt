"""
"""

import asyncio
import logging
import types
from abc import ABCMeta
from ssl import SSLContext
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    NoReturn,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

import aiohttp
from aiohttp.hdrs import RETRY_AFTER as _RETRY_AFTER
from typing_extensions import Self
from yarl import URL

from aioqbt import exc
from aioqbt._compat import cached_property
from aioqbt._paramdict import ParamDict
from aioqbt.mapper import ObjectMapper
from aioqbt.version import APIVersion, ClientVersion

if TYPE_CHECKING:
    from aioqbt.api import (
        AppAPI,
        AuthAPI,
        LogAPI,
        RSSAPI,
        SearchAPI,
        SyncAPI,
        TorrentsAPI,
        TransferAPI,
    )

__all__ = (
    "APIClient",
    "APIGroup",
    "create_client",
)

T = TypeVar("T")
K = TypeVar("K")


class APIClient:
    """
    Represent a remote qBittorrent client.
    """

    def __init__(
        self,
        base_url: str,
        *,
        mapper: Optional[ObjectMapper] = None,
        http: Optional[aiohttp.ClientSession] = None,
        ssl: Optional[SSLContext] = None,
        client_version: Optional[ClientVersion] = None,
        api_version: Optional[APIVersion] = None,
        logout_when_close: Optional[bool] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        if logger is None:
            logger = logging.getLogger(
                "%s.%s" % (type(self).__module__, type(self).__qualname__),
            )

        base_url = base_url.rstrip("/")

        if mapper is None:
            mapper = ObjectMapper()

        if http is None:
            http = aiohttp.ClientSession()
            http_owner = True
        else:
            http_owner = False

        context: Dict[Any, Any] = {
            "mapper": mapper,
            "client_version": client_version,
            "api_version": api_version,
        }

        self._logger = logger
        self._mapper = mapper
        self._context = context
        self._http: Optional[aiohttp.ClientSession] = http
        self._http_owner = http_owner
        self._ssl = ssl
        self.base_url = base_url
        self._retry_statuses = {
            429,  # Too many requests
            503,  # Service unavailable
            502,  # Bad gateway: reverse proxy may be overloaded
        }
        self._logout_when_close = logout_when_close

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.base_url!r}>"

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[types.TracebackType],
    ) -> None:
        await self.close()

    def is_closed(self) -> bool:
        """Tell whether client is closed"""
        return self._http is None

    @property
    def closed(self) -> bool:
        # deprecated, prefer `is_closed()` to `closed` property
        return self._http is None

    async def close(self) -> None:
        """
        Close client.

        Release/detach resources acquired by client.
        """

        if self._http is None:
            return

        if self._logout_when_close:
            try:
                await self.auth.logout()
            except exc.ForbiddenError:
                pass

        # break cycle references to help GC.
        vars_dict = vars(self)

        for name in ("app", "auth", "log", "sync", "torrents", "transfer"):
            if name not in vars_dict:
                continue
            group = getattr(self, name, None)
            if isinstance(group, APIGroup):
                group._close()
                vars_dict.pop(name, None)

        # Close if owned
        if self._http_owner:
            await self._http.close()

        # Detach ClientSession
        self._http = None

    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Any = None,
        data: Any = None,
        max_attempts: int = 3,
        retry_delay: float = 5,
        ssl: Optional[SSLContext] = None,
        **kwargs: object,
    ) -> aiohttp.ClientResponse:
        """
        Send an HTTP request and return a response object.

        Argument ``method`` specifies the HTTP method (e.g. ``GET``)
        while ``endpoint`` the API endpoint (e.g. ``torrents/info``).

        ``params`` forms the query string of the request URL.
        ``data`` is the payload in the request body.
        See the underlying :meth:`ClientSession.request <aiohttp.ClientSession.request>`
        for their allowed values.

        ``max_attempts`` is the maximum number of attempts.
        Retry is performed if two additional conditions are satisfied:

        * ``GET`` or ``HEAD`` requets
        * Remote disconnection, or repsonse status
          429 (Too many requests), 503 (Service unavailable), or 502 (Bad gateway).

        The result is :class:`aiohttp.ClientResponse`, and should be used in ``async with``.

        :param str method: HTTP method.
        :param str endpoint: API endpoint.
        :param params: parameters in query string
        :param data: data in request body
        :param int max_attempts: maximum number of attempts
        :param float retry_delay: maximum delay between attempts
        :param ssl: :class:`~ssl.SSLContext`, optional
        :raise APIError: API errors (non-``200`` status).
        :raise aiohttp.ClientError: connection errors
        :return: :class:`~aiohttp.ClientResponse`
        """

        if max_attempts <= 0:
            raise ValueError(f"max_attempts <= 0: {max_attempts!r}")
        elif method.upper() not in ("GET", "HEAD"):
            max_attempts = 1

        if self._http is None:
            raise RuntimeError("closed client")

        url = self.base_url + "/" + endpoint.lstrip("/")

        if isinstance(params, ParamDict):
            params = params.to_dict()

        if isinstance(data, ParamDict):
            data = data.to_dict()

        if ssl is None:
            ssl = self._ssl

        attempt_count = 1
        while True:
            resp: Optional[aiohttp.ClientResponse] = None
            resp_body: bytes = b""

            try:
                resp = await self._http.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    ssl=ssl,
                    raise_for_status=False,
                    **kwargs,
                )

                if resp.status == 200:
                    return resp

                # treat all status except 200 an error
                # Read the response before release the response
                resp_body = await resp.read()
                resp.release()

                raise aiohttp.ClientResponseError(
                    resp.request_info,
                    resp.history,
                    status=resp.status,
                    message=str(resp.reason),
                    headers=resp.headers,
                )
            except (
                aiohttp.ServerDisconnectedError,
                aiohttp.ClientResponseError,
            ) as ex:
                self._logger.warning(
                    "Request %d/%d: %s %r",
                    attempt_count,
                    max_attempts,
                    method,
                    _real_url(url, params),
                    exc_info=True,
                )
                last_exc = ex

            if attempt_count < max_attempts:
                should_retry, sleeping_time = self._retry_strategy(retry_delay, last_exc, resp)

                if should_retry:
                    attempt_count += 1
                    await asyncio.sleep(sleeping_time)
                    continue

            self._handle_error(last_exc, resp, resp_body)

    def _retry_strategy(
        self,
        retry_pause: float,
        ex: BaseException,
        resp: Optional[aiohttp.ClientResponse],
    ) -> Tuple[bool, float]:
        """
        Ruturn a tuple of a bool and a sleeping time.

        The bool indicate whether retry should be made.
        """

        if resp is None:
            # The issues are related to sockets or network connections.
            if isinstance(ex, aiohttp.ServerDisconnectedError):
                # retry if TCP was probably reset
                return True, retry_pause

            return False, 0

        if resp.status not in self._retry_statuses:
            return False, 0

        retry_after: Optional[int] = None
        if _RETRY_AFTER in resp.headers:
            # the remote seems busy or in maintenance
            try:
                # Support second format only
                retry_after = int(resp.headers[_RETRY_AFTER])

                if retry_after < 0:
                    retry_after = None
            except ValueError:
                # Date format is not supported
                # It usually suggests relatively long unavailability.
                return False, 0

        if retry_after is None:
            return True, retry_pause
        elif retry_after <= retry_pause:
            # below our expected limit
            return True, retry_after
        else:
            return False, 0

    def _handle_error(
        self,
        error: Exception,
        resp: Optional[aiohttp.ClientResponse],
        resp_body: bytes,
    ) -> NoReturn:
        """
        Handle errors which are not retryable.
        """

        if resp is None:
            # raise the last error if no resp available
            raise error

        try:
            message = resp_body.decode("utf-8", "strict")
        except UnicodeDecodeError:
            message = ""

        exc_class = exc._ERROR_TABLE.get(resp.status, exc.APIError)
        raise exc_class.from_response(resp, message) from error

    async def request_text(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> str:
        """
        Send a request and return a str.
        """

        resp = await self.request(method, endpoint, **kwargs)
        async with resp:
            return await resp.text(encoding="utf-8")

    async def request_json(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Any:
        """
        Send a request and return a JSON-decoded object.
        """
        resp = await self.request(method, endpoint, **kwargs)
        async with resp:
            result = await resp.json()

        return result

    def _create_object(self, rtype: Type[T], data: Mapping[str, Any]) -> T:
        return self._mapper.create_object(rtype, data, self._context)

    def _create_list(self, rtype: Type[T], data: Sequence[Mapping[str, Any]]) -> List[T]:
        return self._mapper.create_list(rtype, data, self._context)

    def _create_dict(self, rtype: Type[T], data: Mapping[K, Mapping[str, Any]]) -> Dict[K, T]:
        return self._mapper.create_dict(rtype, data, self._context)

    @property
    def client_version(self) -> Optional[ClientVersion]:
        """qBittorrent client version"""
        return self._context.get("client_version")

    @client_version.setter
    def client_version(self, version: Optional[ClientVersion]) -> None:
        self._context["client_version"] = version

    @property
    def api_version(self) -> Optional[APIVersion]:
        """qBittorrent API version"""
        return self._context.get("api_version")

    @api_version.setter
    def api_version(self, version: Optional[APIVersion]) -> None:
        self._context["api_version"] = version

    @cached_property
    def app(self) -> "AppAPI":
        """
        Application API methods.
        """
        from aioqbt.api.app import AppAPI

        return AppAPI(self)

    @cached_property
    def auth(self) -> "AuthAPI":
        """
        Authentication API methods.
        """
        from aioqbt.api.auth import AuthAPI

        return AuthAPI(self)

    @cached_property
    def log(self) -> "LogAPI":
        """
        Log API methods.
        """
        from aioqbt.api.log import LogAPI

        return LogAPI(self)

    @cached_property
    def rss(self) -> "RSSAPI":
        """
        RSS API methods.
        """
        from aioqbt.api.rss import RSSAPI

        return RSSAPI(self)

    @cached_property
    def search(self) -> "SearchAPI":
        """
        Search API methods.
        """
        from aioqbt.api.search import SearchAPI

        return SearchAPI(self)

    @cached_property
    def sync(self) -> "SyncAPI":
        """
        Sync API methods.
        """
        from aioqbt.api.sync import SyncAPI

        return SyncAPI(self)

    @cached_property
    def torrents(self) -> "TorrentsAPI":
        """
        Torrents API methods.
        """
        from aioqbt.api.torrents import TorrentsAPI

        return TorrentsAPI(self)

    @cached_property
    def transfer(self) -> "TransferAPI":
        """
        Transfer API methods.
        """
        from aioqbt.api.transfer import TransferAPI

        return TransferAPI(self)


class APIGroup(metaclass=ABCMeta):
    """
    API group of methods.
    """

    _client_ref: Optional["APIClient"] = None

    def __init__(self, client: "APIClient"):
        # do not keep the reference if closed
        self._client_ref = None if client.is_closed() else client

    def _client(self) -> "APIClient":
        client = self._client_ref

        if client is None:
            raise RuntimeError("closed client")

        return client

    def _close(self) -> None:
        self._client_ref = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        return await self._client().request(method, endpoint, **kwargs)

    async def _request_text(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> str:
        return await self._client().request_text(method, endpoint, **kwargs)

    async def _request_json(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Any:
        return await self._client().request_json(method, endpoint, **kwargs)

    async def _request_mapped_object(
        self,
        rtype: Type[T],
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> T:
        client = self._client()
        result = await client.request_json(method, endpoint, **kwargs)
        return client._create_object(rtype, result)

    async def _request_mapped_list(
        self,
        rtype: Type[T],
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> List[T]:
        client = self._client()
        result = await client.request_json(method, endpoint, **kwargs)
        return client._create_list(rtype, result)

    async def _request_mapped_dict(
        self,
        rtype: Type[T],
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Dict[str, T]:
        client = self._client()
        result = await client.request_json(method, endpoint, **kwargs)
        return client._create_dict(rtype, result)


def _real_url(url: str, params: Optional[Mapping[str, Any]] = None) -> str:
    url_obj = URL(url)
    if params is not None:
        url_obj = url_obj.with_query(params)

    return str(url_obj)


async def create_client(
    url: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    *,
    logout_when_close: Optional[bool] = None,
    http: Optional[aiohttp.ClientSession] = None,
    ssl: Optional[SSLContext] = None,
) -> APIClient:
    """
    Create :class:`APIClient`.

    When both ``username`` and ``password`` are given,
    the returned client will have been successfully authenticated and automatically configured.
    Otherwise, :exc:`LoginError <aioqbt.exc.LoginError>` is raised.

    If they are omitted, :meth:`client.auth.login() <.AuthAPI.login>` need to be called manually.

    If the URL host is expresed in IP address instead of domain name,
    session cookies are not preserved properly and
    subsequent requests result in :exc:`~.ForbiddenError`.
    See :issue:`GH-2 <2#issuecomment-1925461178>` for details.

    :param str url: URL to WebUI API, for example, ``https://localhost:8080/api/v2/``
    :param str username: login name
    :param str password: login password
    :param logout_when_close: whether logout during :meth:`~.APIClient.close`.
    :param http: :class:`aiohttp.ClientSession` object
    :param ssl: :class:`ssl.SSLContext` for custom TLS connections
    :raises LoginError: if authentication is failed.
    """
    if (username is None) != (password is None):
        raise TypeError("Specify both username and password arguments, or neither of them")

    if logout_when_close is None:
        logout_when_close = username is not None

    mapper = ObjectMapper()
    client = APIClient(
        base_url=url,
        mapper=mapper,
        http=http,
        ssl=ssl,
        logout_when_close=logout_when_close,
    )

    if username is not None:
        assert isinstance(password, str)
        try:
            await client.auth.login(username, password)
        except exc.LoginError:
            await client.close()
            raise

    try:
        client_version, api_version = await asyncio.gather(
            client.app.version(),
            client.app.webapi_version(),
        )
    except exc.ForbiddenError:
        pass
    else:
        client.client_version = ClientVersion.parse(client_version)
        client.api_version = APIVersion.parse(api_version)

    return client


#
# def _find_localtime():
#     from datetime import timedelta, timezone
#     from time import localtime
#
#     tm = localtime()
#     return timezone(timedelta(seconds=tm.tm_gmtoff), tm.tm_zone)
#
#
# _LOCAL_TIMEZONE = _find_localtime()


def since(version: Union[APIVersion, Tuple[int, int, int]]) -> Callable[[T], T]:
    """
    Annotate function with API version.
    """

    if not isinstance(version, APIVersion):
        version = APIVersion(*version)

    def decorator(fn: T) -> T:
        fn._api_version = version  # type: ignore[attr-defined]
        return fn

    return decorator


@overload
def virtual(fn: None) -> Callable[[T], T]: ...


@overload
def virtual(fn: T) -> T: ...


def virtual(fn: Any = None) -> Any:
    """
    Mark function not backed by endpoint.
    """
    if fn is None:
        return virtual  # pragma: no cover
    else:
        return fn
