import json
from typing import Any, Mapping

from aioqbt.api.types import BuildInfo
from aioqbt.client import APIGroup
from aioqbt.version import version_check

__all__ = ("AppAPI",)


class AppAPI(APIGroup):
    """
    API methods under ``app``.
    """

    async def version(self) -> str:
        return await self._request_text(
            "GET",
            "app/version",
        )

    async def webapi_version(self) -> str:
        return await self._request_text(
            "GET",
            "app/webapiVersion",
        )

    async def build_info(self) -> BuildInfo:
        version_check(self._client().api_version, (2, 3, 0))

        return await self._request_mapped_object(
            BuildInfo,
            "GET",
            "app/buildInfo",
        )

    async def shutdown(self):
        return await self._request_text(  # pragma: no cover
            "POST",
            "app/shutdown",
        )

    # Under construction
    # async def preferences(self) -> Dict[str, Any]:
    #     return await self._request_json(
    #         "GET",
    #         "app/preferences",
    #     )

    async def set_preferences(self, prefs: Mapping[str, Any]):
        """
        :param prefs: a mapping of preferences to update.
        """
        prefs = dict(prefs)
        data = {
            "json": json.dumps(prefs),
        }

        await self._request_text(
            "POST",
            "app/setPreferences",
            data=data,
        )

    async def default_save_path(self) -> str:
        return await self._request_text(
            "GET",
            "app/defaultSavePath",
        )
