import pytest

from aioqbt.api.types import BuildInfo
from aioqbt.client import APIClient


@pytest.mark.asyncio
async def test_app(client: APIClient):
    version = await client.app.version()
    assert isinstance(version, str)
    assert version.startswith("v4.")

    webapi_version = await client.app.webapi_version()
    assert isinstance(webapi_version, str)
    assert webapi_version.startswith("2.")

    build_info = await client.app.build_info()
    assert isinstance(build_info, BuildInfo)
    assert isinstance(build_info.qt, str)
    assert isinstance(build_info.libtorrent, str)
    assert isinstance(build_info.openssl, str)

    default_save_path = await client.app.default_save_path()
    assert isinstance(default_save_path, str)
    assert default_save_path.endswith("qBittorrent/downloads/")
