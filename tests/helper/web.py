import contextlib
import socket
from typing import AsyncIterator, Awaitable, Callable

from aiohttp import web

RequestHandler = Callable[[web.BaseRequest], Awaitable[web.StreamResponse]]


@contextlib.asynccontextmanager
async def temporary_site(runner: web.BaseRunner, port: int = 0) -> AsyncIterator[str]:
    # bind a TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", port))

    # start server site
    site = web.SockSite(runner, sock)
    await site.start()

    # construct site URL
    host, port = sock.getsockname()
    url = f"http://localhost:{port}"

    try:
        yield url
    finally:
        # shutdown server and socket
        await site.stop()
        sock.close()


@contextlib.asynccontextmanager
async def temporary_web_server(
    handler: RequestHandler,
    port: int = 0,
) -> AsyncIterator[str]:
    # start web server
    server = web.Server(handler)
    runner = web.ServerRunner(server)
    await runner.setup()

    async with temporary_site(runner, port) as url:
        yield url
