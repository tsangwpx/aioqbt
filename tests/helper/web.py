import contextlib
import socket
from typing import Awaitable, Callable

from aiohttp import web


@contextlib.asynccontextmanager
async def temporary_site(runner: web.BaseRunner):
    # bind a random TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))

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
async def temporary_site_handler(
    handler: Callable[[web.BaseRequest], Awaitable[web.StreamResponse]],
):
    # start web server
    server = web.Server(handler)
    runner = web.ServerRunner(server)
    await runner.setup()

    async with temporary_site(runner) as url:
        yield url
