from typing import Optional

from aioqbt._paramdict import ParamDict
from aioqbt.api.types import SyncMainData, SyncTorrentPeers
from aioqbt.bittorrent import InfoHash
from aioqbt.client import APIGroup

__all__ = ("SyncAPI",)


# Result from sync/maindata and sync/torrentPeers are "differenced":
# - "rid" key always exist
# - "full_update" is either true or missing
# - other attributes are missing if unchanged
# - complex/nested structure, eg, dict and list, are also "differenced"
# Default values are assigned to the missing attributes of the result:
# - "full_update" is either true or false
# For SyncMainData,
# - "torrents" and "categories" attributes are empty dict when missing
# - "*_remove" attributes are empty list when missing
# For TorrentPeers,
#


class SyncAPI(APIGroup):
    """
    API methods under ``sync``.

    In Sync APIs, entries may be omitted in the returned dict objects
    if their values are unchanged.

    .. note::

        Sync API support is experimental. Methods and results may
        change without notice.

    """

    async def maindata(
        self,
        rid: Optional[int] = None,
    ) -> SyncMainData:
        params = ParamDict()
        params.optional_int("rid", rid)

        return await self._request_mapped_object(
            SyncMainData,
            "GET",
            "sync/maindata",
            params=params,
        )

    async def torrent_peers(
        self,
        hash: InfoHash,
        rid: Optional[int] = None,
    ) -> SyncTorrentPeers:
        params = ParamDict.with_hash(hash)
        params.optional_int("rid", rid)

        return await self._request_mapped_object(
            SyncTorrentPeers,
            "GET",
            "sync/torrentPeers",
            params=params,
        )
