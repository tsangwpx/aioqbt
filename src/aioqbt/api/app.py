import json
from typing import List, Mapping, Optional

from aioqbt._paramdict import ParamDict
from aioqbt.api.types import BuildInfo, NetworkInterface, Preferences
from aioqbt.client import APIGroup
from aioqbt.version import version_check

__all__ = ("AppAPI",)


class AppAPI(APIGroup):
    """
    API methods under ``app``.
    """

    async def version(self) -> str:
        """qBittorrent version."""
        return await self._request_text(
            "GET",
            "app/version",
        )

    async def webapi_version(self) -> str:
        """WebUI API version."""
        return await self._request_text(
            "GET",
            "app/webapiVersion",
        )

    async def build_info(self) -> BuildInfo:
        """Build information."""
        version_check(self._client().api_version, (2, 3, 0))

        return await self._request_mapped_object(
            BuildInfo,
            "GET",
            "app/buildInfo",
        )

    async def shutdown(self):
        """Shut down qBittorrent client."""
        return await self._request_text(  # pragma: no cover
            "POST",
            "app/shutdown",
        )

    async def preferences(self) -> Preferences:
        """Get application preferences."""
        return await self._request_json(
            "GET",
            "app/preferences",
        )

    async def set_preferences(self, prefs: Mapping[str, object]):
        """
        Set application preferences.

        :param prefs: a mapping of preferences to update.
        """
        prefs = dict(prefs)
        # plus sign (+) were not decoded as space in v4.1.5 or earlier.
        # JSON.dumps() are invalid with default separators argument.
        # Removing spaces in separators allows parsing JSON correctly
        # though plus signs are still not decoded as spaces.
        # This should behave similarly to WebUI.
        # https://github.com/qbittorrent/qBittorrent/issues/10451
        data = {
            "json": json.dumps(prefs, separators=(",", ":")),
        }

        await self._request_text(
            "POST",
            "app/setPreferences",
            data=data,
        )

    async def default_save_path(self) -> str:
        """Default save path for storing downloaded files"""
        return await self._request_text(
            "GET",
            "app/defaultSavePath",
        )

    async def network_interface_list(self) -> List[NetworkInterface]:
        """Network interfaces."""
        # since v4.2.0, API v2.3.0
        return await self._request_mapped_list(
            NetworkInterface,
            "GET",
            "app/networkInterfaceList",
        )

    async def network_interface_address_list(self, iface: Optional[str] = None) -> List[str]:
        """Network addresses."""
        # since v4.2.0, API v2.3.0
        params = ParamDict()
        params.put("iface", iface, optional=False, prepare=str, default="")

        return await self._request_json(
            "GET",
            "app/networkInterfaceAddressList",
            params=params,
        )
