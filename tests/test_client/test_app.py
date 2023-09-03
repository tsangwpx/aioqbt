import ipaddress

import pytest

from aioqbt.api.types import BuildInfo, NetworkInterface
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


@pytest.mark.asyncio
async def test_interfaces(client: APIClient):
    if not version_satisfy(client.api_version, (2, 3, 0)):
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
        ipaddress.ip_address(addr)
