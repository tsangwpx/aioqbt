import pytest

from aioqbt.api.types import BuildInfo
from aioqbt.client import APIClient
from aioqbt.version import version_satisfy


@pytest.mark.asyncio
async def test_app(client: APIClient):
    version = await client.app.version()
    assert isinstance(version, str)
    assert version.startswith("v4.")

    webapi_version = await client.app.webapi_version()
    assert isinstance(webapi_version, str)
    assert webapi_version.startswith("2.")

    if version_satisfy(client.api_version, (2, 3, 0)):
        build_info = await client.app.build_info()
        assert isinstance(build_info, BuildInfo)
        assert isinstance(build_info.qt, str)
        assert isinstance(build_info.libtorrent, str)
        assert isinstance(build_info.openssl, str)

    default_save_path = await client.app.default_save_path()
    assert isinstance(default_save_path, str)
