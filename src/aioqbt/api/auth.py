from aioqbt import exc
from aioqbt.client import APIClient, APIGroup

__all__ = ("AuthAPI",)


async def _auth_login(client: APIClient, username: str, password: str):
    resp = await client.request(
        "POST",
        "auth/login",
        data={
            "username": str(username),
            "password": str(password),
        },
    )

    async with resp:
        res = await resp.read()

        if res != b"Ok.":
            ex = exc.LoginError.from_response(resp)
            ex.message = res.decode("utf-8")
            raise ex


class AuthAPI(APIGroup):
    """
    API methods under ``auth``.
    """

    async def login(self, username: str, password: str):
        return await _auth_login(self._client(), username, password)

    async def logout(self):
        # Seem that logout always succeed
        await self._request_text(
            "POST",
            "auth/logout",
        )
