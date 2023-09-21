"""
"""
import asyncio
import logging
from abc import ABCMeta
from ssl import SSLContext
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import aiohttp
from aiohttp.hdrs import RETRY_AFTER as _RETRY_AFTER
from yarl import URL

from aioqbt import exc
from aioqbt._compat import cached_property
from aioqbt._paramdict import ParamDict
from aioqbt.mapper import ObjectMapper
from aioqbt.version import APIVersion, ClientVersion

if TYPE_CHECKING:
    from aioqbt.api import AppAPI, AuthAPI, LogAPI, SyncAPI, TorrentsAPI, TransferAPI

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
        logger: Optional[logging.Logger] = None,
    ):
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

    def __repr__(self):
        return f"<{type(self).__name__} {self.base_url!r}>"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def is_closed(self) -> bool:
        """Tell whether client is closed"""
        return self._http is None

    @property
    def closed(self) -> bool:
        # deprecated, prefer `is_closed()` to `closed` property
        return self._http is None

    async def close(self):
        """
        Close client.

        Release/detach resources acquired by client.
        """

        if self._http is None:
            return

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
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """
        Send an HTTP request and return a response object.

        Response objects need close after use.

        :param str method: request method
        :param str endpoint: endpoint path, e.g. ``torrents/info``
        :param params: parameters in query string
        :param data: data in request body
        :param int max_attempts: maximum number of attempts
        :param float retry_delay: maximum delay between attempts
        :param ssl: :class:`~ssl.SSLContext`, optional
        :raise APIError: API errors
        :raise aiohttp.ClientError: connection errors
        :return: :class:`~aiohttp.ClientResponse`
        """

        if max_attempts <= 0:
            raise ValueError(f"max_attempts <= 0: {max_attempts!r}")

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
                aiohttp.ServerTimeoutError,
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

            if resp is None:
                # the server is unreachable or the socket is reset
                should_retry = attempt_count < max_attempts
            else:
                # the server is busy or in error
                # retry in particular cases
                should_retry = attempt_count < max_attempts and (
                    resp.status in self._retry_statuses or _RETRY_AFTER in resp.headers
                )

            if should_retry:
                attempt_count += 1

                sleeping_time = retry_delay
                if resp is not None:
                    try:
                        sleeping_time = min(sleeping_time, int(resp.headers[_RETRY_AFTER]))
                    except (KeyError, ValueError):
                        pass

                await asyncio.sleep(sleeping_time)
            else:
                self._handle_error(last_exc, resp, resp_body)

    def _handle_error(
        self,
        error: Exception,
        resp: Optional[aiohttp.ClientResponse],
        resp_body: bytes,
    ):
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
        **kwargs,
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
        **kwargs,
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
    def client_version(self, version: Optional[ClientVersion]):
        self._context["client_version"] = version

    @property
    def api_version(self) -> Optional[APIVersion]:
        """qBittorrent API version"""
        return self._context.get("api_version")

    @api_version.setter
    def api_version(self, version: Optional[APIVersion]):
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

    def _close(self):
        self._client_ref = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        return await self._client().request(method, endpoint, **kwargs)

    async def _request_text(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> str:
        return await self._client().request_text(method, endpoint, **kwargs)

    async def _request_json(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Any:
        return await self._client().request_json(method, endpoint, **kwargs)

    async def _request_mapped_object(
        self,
        rtype: Type[T],
        method: str,
        endpoint: str,
        **kwargs,
    ) -> T:
        client = self._client()
        result = await client.request_json(method, endpoint, **kwargs)
        return client._create_object(rtype, result)

    async def _request_mapped_list(
        self,
        rtype: Type[T],
        method: str,
        endpoint: str,
        **kwargs,
    ) -> List[T]:
        client = self._client()
        result = await client.request_json(method, endpoint, **kwargs)
        return client._create_list(rtype, result)

    async def _request_mapped_dict(
        self,
        rtype: Type[T],
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Dict[Any, T]:
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
    http: Optional[aiohttp.ClientSession] = None,
    ssl: Optional[SSLContext] = None,
) -> APIClient:
    """
    Create :class:`APIClient`.

    When both ``username`` and ``password`` are given,
    the returned client will be authenticated successfully and automatically configured.
    Otherwise, :exc:`LoginError <aioqbt.exc.LoginError>` is raised.

    If they are omitted, :meth:`client.auth.login() <.AuthAPI.login>` need to be called manually.

    :param str url: URL to WebUI API, for example, ``https://localhost:8080/api/v2/``
    :param str username: login name
    :param str password: login password
    :param http: :class:`aiohttp.ClientSession` object
    :param ssl: :class:`ssl.SSLContext` for custom TLS connections
    :raises LoginError: if authentication is failed.
    """
    if (username is None) != (password is None):
        raise TypeError("Specify both username and password arguments, or neither of them")

    mapper = ObjectMapper()
    client = APIClient(
        base_url=url,
        mapper=mapper,
        http=http,
        ssl=ssl,
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

    def decorator(fn):
        fn._api_version = version
        return fn

    return decorator


def virtual(fn=None):
    """
    Mark function not backed by endpoint.
    """
    if fn is None:
        return virtual  # pragma: no cover
    else:
        return fn
