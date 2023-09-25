import warnings
from typing import Any, Dict, List, Tuple, Union

import pytest
from helper.lang import retry_assert
from typing_extensions import get_origin, get_type_hints

from aioqbt.api.types import BuildInfo, NetworkInterface, Preferences
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
async def test_preferences(client: APIClient):
    prefs: Preferences
    prefs = await client.app.preferences()

    assert isinstance(prefs, dict), type(prefs)

    annotations = get_type_hints(Preferences)
    missing: List[str] = []
    invalid: Dict[str, Tuple[Any, Any]] = {}

    for name, tp in annotations.items():
        try:
            value = prefs.pop(name)  # type: ignore[misc]
        except KeyError:
            missing.append(name)
            continue

        if tp in {int, float, str, bool}:
            tp_origin = tp
        else:
            tp_origin = get_origin(tp)

        assert tp_origin is not None, tp

        if tp_origin is Union:
            continue

        assert tp_origin in (bool, int, str, float, list, dict), tp_origin

        if not isinstance(value, tp_origin):
            invalid[name] = (tp, type(value))

    header = f"client=v{client.client_version}, api_version={client.api_version}"

    if missing:
        # missing keys occurred across versions
        msg = ",".join(missing)
        print(f"Missing keys ({header}):\n{msg!s}")

    # show warning instead of failing tests

    if prefs:
        msg = "\n".join(f"{k}: {type(v)}" for k, v in prefs.items())
        warnings.warn(UserWarning(f"Extra prefs ({header}):\n{msg}"))

    if invalid:
        msg = "\n".join(f"{s}: {a}, {b}" for s, (a, b) in invalid.items())
        warnings.warn(UserWarning(f"Invalid typing ({header}):\n{msg}"))


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
