import pytest
import pytest_asyncio
from helper.service import LoginInfo, login_session_context, parse_login_env, server_process

from aioqbt.client import APIClient


@pytest.fixture(scope="session")
def mock_login(tmp_path_factory):
    login = parse_login_env("MOCK_SERVER")
    if login is not None:
        yield login
        return

    profile_path = tmp_path_factory.mktemp("server_profile", False)
    with server_process(profile_path) as (host, port):
        yield LoginInfo(
            url=f"http://{host}:{port}/api/v2",
            username="admin",
            password="adminadmin",
        )


@pytest_asyncio.fixture
async def client(mock_login: LoginInfo):
    async with login_session_context(mock_login) as client:
        yield client


@pytest_asyncio.fixture
async def temp_prefs(client: APIClient):
    """restore preferences after change"""
    original = await client.app.preferences()

    yield dict(original)

    latest = await client.app.preferences()

    changed = {k: v for k, v in original.items() if v != latest.get(k)}

    if changed:
        await client.app.set_preferences(changed)
