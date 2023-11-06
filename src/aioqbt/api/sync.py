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
    Sync APIs.

    In Sync APIs, changes between requests are returned in dict-like objects.
    Keys may be omitted if their values are unchanged.

    """

    async def maindata(
        self,
        rid: Optional[int] = None,
    ) -> SyncMainData:
        """
        Obtain sync data.

        ``rid`` in the previous sync data may be passed to the ``rid`` argument
        to obtain a difference update.

        If ``full_update=True`` in the resultant object, the data is a full update.
        Otherwise, the data only contains changes since the last sync request.

        """
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
        """
        Obtain peers for a torrent.

        ``rid`` and ``full_update`` share similar meanings in :meth:`.maindata`.

        """
        params = ParamDict.with_hash(hash)
        params.optional_int("rid", rid)

        return await self._request_mapped_object(
            SyncTorrentPeers,
            "GET",
            "sync/torrentPeers",
            params=params,
        )
