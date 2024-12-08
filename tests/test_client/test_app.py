import re

import pytest
from helper.lang import retry_assert

from aioqbt.api.types import BuildInfo, NetworkInterface, Preferences
from aioqbt.client import APIClient
from aioqbt.version import APIVersion


@pytest.mark.asyncio
async def test_app(client: APIClient):
    version = await client.app.version()
    assert isinstance(version, str)
    assert re.match(r"^v\d+\.", version) is not None, version

    webapi_version = await client.app.webapi_version()
    assert isinstance(webapi_version, str)
    assert webapi_version.startswith("2.")

    if APIVersion.compare(client.api_version, (2, 3, 0)) >= 0:
        build_info = await client.app.build_info()
        assert isinstance(build_info, BuildInfo)
        assert isinstance(build_info.qt, str)
        assert isinstance(build_info.libtorrent, str)
        assert isinstance(build_info.openssl, str)

    default_save_path = await client.app.default_save_path()
    assert isinstance(default_save_path, str)


@pytest.mark.asyncio
async def test_preferences(client: APIClient):
    prefs: Preferences
    prefs = await client.app.preferences()

    assert isinstance(prefs, dict), type(prefs)


@pytest.mark.asyncio
async def test_set_preferences(client: APIClient):
    changes = Preferences()
    changes["alt_dl_limit"] = 7 * 1024

    await client.app.set_preferences(changes)

    @retry_assert
    async def assert_updated():
        prefs = await client.app.preferences()
        assert prefs["alt_dl_limit"] == changes["alt_dl_limit"], prefs["alt_dl_limit"]

    await assert_updated()


@pytest.mark.asyncio
async def test_interfaces(client: APIClient):
    if APIVersion.compare(client.api_version, (2, 3, 0)) < 0:
        pytest.skip("networkInterfaceList are available since API v2.3.0")

    interfaces = await client.app.network_interface_list()
    assert isinstance(interfaces, list)

    for iface in interfaces:
        assert isinstance(iface, NetworkInterface)
        assert isinstance(iface.name, str)
        assert isinstance(iface.value, str)

    addresses = await client.app.network_interface_address_list()
    assert isinstance(addresses, list)

    for addr in addresses:
        assert isinstance(addr, str)


@pytest.mark.asyncio
async def test_send_test_email(client: APIClient) -> None:
    if APIVersion.compare(client.api_version, (2, 11, 0)) < 0:
        pytest.skip("Require API v2.11.0")

    # the endpoint always succeeds despite email settings.
    await client.app.send_test_email()
