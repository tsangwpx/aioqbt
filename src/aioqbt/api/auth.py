from typing import Optional

import aiohttp

from aioqbt import exc
from aioqbt.client import APIClient, APIGroup

__all__ = ("AuthAPI",)


async def _auth_login(client: APIClient, username: str, password: str) -> None:
    resp = await client.request(
        "POST",
        "auth/login",
        data={
            "username": str(username),
            "password": str(password),
        },
        raise_for_status=False,
    )

    async with resp:
        try:
            # body should have been cached in the response
            res = await resp.read()
        except aiohttp.ClientConnectionError:
            res = b""

    # the API version is unavailable before login.
    # Before v5.2.0, the login endpoint return 200 with either "Ok." or "Fails.".
    if resp.status == 200 and res in (b"Ok.", b"Fails."):
        if res == b"Ok.":
            return
        else:
            ex = exc.LoginError.from_response(resp)
            ex.message = res.decode("utf-8")
            raise ex

    if 200 <= resp.status < 300:
        # the status should either 200 or 401
        return
    else:
        ex = exc.LoginError.from_response(resp)
        ex.message = res.decode("utf-8")

        raise ex


class AuthAPI(APIGroup):
    """
    API methods under ``auth``.
    """

    async def login(self, username: str, password: str) -> None:
        return await _auth_login(self._client(), username, password)

    async def logout(self) -> None:
        # Seem that logout always succeed
        await self._request_text(
            "POST",
            "auth/logout",
        )
