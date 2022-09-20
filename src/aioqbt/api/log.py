from typing import List, Optional

from aioqbt._paramdict import ParamDict
from aioqbt.api.types import LogMessage, LogPeer
from aioqbt.client import APIGroup

__all__ = ("LogAPI",)


class LogAPI(APIGroup):
    """
    API methods under ``log``.
    """

    async def main(
        self,
        normal: Optional[bool] = None,
        info: Optional[bool] = None,
        warning: Optional[bool] = None,
        critical: Optional[bool] = None,
        last_known_id: Optional[int] = None,
    ) -> List[LogMessage]:
        params = ParamDict()
        params.optional_bool("normal", normal)
        params.optional_bool("info", info)
        params.optional_bool("warning", warning)
        params.optional_bool("critical", critical)
        params.optional_int("last_known_id", last_known_id)

        return await self._request_mapped_list(
            LogMessage,
            "GET",
            "log/main",
            params=params,
        )

    async def peers(self, last_known_id: Optional[int] = None) -> List[LogPeer]:
        params = ParamDict()
        params.optional_int("last_known_id", last_known_id)

        return await self._request_mapped_list(
            LogPeer,
            "GET",
            "log/peers",
            params=params,
        )
