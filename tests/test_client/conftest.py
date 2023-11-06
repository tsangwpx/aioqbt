from typing import Any, AsyncIterator, Dict, Iterable, List

import pytest
import pytest_asyncio
from helper.client import LoginInfo, client_context, parse_login_env
from helper.service import server_process

from aioqbt.client import APIClient


@pytest.fixture(scope="session")
def mock_login(tmp_path_factory: pytest.TempPathFactory) -> Iterable[LoginInfo]:
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


@pytest.fixture(scope="session")
def client_cookies() -> List[Any]:
    return []


@pytest_asyncio.fixture
async def client(mock_login: LoginInfo, client_cookies: List[Any]) -> AsyncIterator[APIClient]:
    async with client_context(mock_login, client_cookies) as client:
        yield client


@pytest_asyncio.fixture
async def temp_prefs(client: APIClient) -> AsyncIterator[Dict[str, Any]]:
    """restore preferences after change"""
    original = await client.app.preferences()

    yield dict(original)

    latest = await client.app.preferences()

    changed = {k: v for k, v in original.items() if v != latest.get(k)}

    if changed:
        await client.app.set_preferences(changed)
