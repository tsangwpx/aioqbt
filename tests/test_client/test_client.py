import asyncio
from typing import Union

import aiohttp
import aiohttp.web as aiohttp_web
import pytest
from aiohttp.hdrs import RETRY_AFTER
from helper.service import LoginInfo
from helper.web import temporary_site_handler

from aioqbt import exc
from aioqbt.client import APIClient, create_client


@pytest.mark.asyncio
async def test_manual_create_client(mock_login: LoginInfo):
    """Create client without logging in"""
    login = mock_login

    client = await create_client(
        url=login.url,
    )

    async with client:
        assert client.api_version is None
        await client.auth.login(login.username, login.password)


@pytest.mark.asyncio
async def test_login_failed(mock_login: LoginInfo):
    with pytest.raises(exc.LoginError):
        await create_client(
            url=mock_login.url,
            username="badUsername",
            password="badPassword",
        )


@pytest.mark.asyncio
async def test_create_client_params():
    with pytest.raises(TypeError):
        await create_client(
            "http://localhost/does/not/masster",
            username="someUser",
            password=None,
        )


@pytest.mark.asyncio
async def test_closed_errors(mock_login: LoginInfo):
    client = await create_client(
        url=mock_login.url,
        username=mock_login.username,
        password=mock_login.password,
    )
    assert not client.is_closed()

    with pytest.raises(ValueError):
        await client.request("GET", "hello", max_attempts=0)

    await client.close()
    await client.close()
    assert client.is_closed()

    with pytest.raises(RuntimeError):
        await client.request("GET", "whatever")

    with pytest.raises(RuntimeError):
        await client.torrents.info()


@pytest.mark.asyncio
async def test_server_disconnected():
    max_attempts = 3
    retry_delay = 1 / 1000  # 1 ms

    try_count = 0
    futures = set()

    async def task(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        nonlocal try_count
        try_count += 1

        # read the request header or add some delays
        # to avoid "connection reset by peer" in client side
        await reader.read(1)

        writer.close()
        await writer.wait_closed()

    def on_connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        futures.add(asyncio.create_task(task(reader, writer)))

    server = await asyncio.start_server(on_connected, "127.0.0.1")
    sockets = server.sockets
    host, port = sockets[0].getsockname()
    url = f"http://{host}:{port}/api/v2"

    async with APIClient(url) as client:
        with pytest.raises(aiohttp.ServerDisconnectedError):
            resp = await client.request(
                "GET",
                "hello",
                params={"value": "1"},
                retry_delay=retry_delay,
                max_attempts=max_attempts,
            )
            async with resp:
                pass

    assert try_count == max_attempts
    server.close()
    await server.wait_closed()
    await asyncio.wait(futures)


@pytest.mark.asyncio
async def test_retry_after_header():
    max_attempts = 3
    retry_delay = 1 / 1000  # 1 ms

    try_count = 0

    # define request handler
    async def handler(request: aiohttp_web.BaseRequest):
        nonlocal try_count
        try_count += 1

        retry_after = "1"
        if try_count == 2:
            retry_after = "badvalue"

        raise aiohttp_web.HTTPServiceUnavailable(
            headers={
                RETRY_AFTER: retry_after,
            }
        )

    async with temporary_site_handler(handler) as url, APIClient(url) as client:
        with pytest.raises(exc.APIError, match="Service Unavailable"):
            resp = await client.request(
                "GET",
                "hello",
                retry_delay=retry_delay,
                max_attempts=max_attempts,
            )
            async with resp:
                pass

        assert try_count == max_attempts


@pytest.mark.parametrize(
    ("body", "match"),
    (
        (None, "Bad Request"),
        ("dummy dummy", "dummy dummy"),
        ("\u4e2d\u6587", "\\u4e2d\\u6587"),
        (b"\x80", "Bad Request"),
    ),
)
@pytest.mark.asyncio
async def test_error_message(body: Union[str, bytes], match):
    # define request handler
    async def handler(request: aiohttp_web.BaseRequest):
        return aiohttp_web.Response(
            status=aiohttp_web.HTTPBadRequest.status_code,
            body=body,
        )

    async with temporary_site_handler(handler) as url, APIClient(url) as client:
        with pytest.raises(exc.BadRequestError, match=match):
            await client.request("GET", "/")
