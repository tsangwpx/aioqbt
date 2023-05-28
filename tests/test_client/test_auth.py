import pytest
from helper.service import LoginInfo

from aioqbt import exc
from aioqbt.client import create_client


@pytest.mark.asyncio
async def test_login_failed(mock_login: LoginInfo):
    with pytest.raises(exc.LoginError):
        await create_client(
            url=mock_login.url,
            username="badUsername",
            password="badPassword",
        )


@pytest.mark.asyncio
async def test_logout(mock_login: LoginInfo):
    client = await create_client(
        url=mock_login.url,
        username=mock_login.username,
        password=mock_login.password,
    )

    async with client:
        await client.auth.logout()

        with pytest.raises(exc.ForbiddenError):
            await client.app.version()
