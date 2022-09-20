import pytest
from helper.torrent import make_torrent_single, temporary_torrents

from aioqbt.api.types import SyncMainData, SyncTorrentPeers
from aioqbt.client import APIClient


@pytest.mark.asyncio
async def test_maindata(client: APIClient):
    data = await client.sync.maindata()
    assert isinstance(data, SyncMainData)
    assert isinstance(data.rid, int)


@pytest.mark.asyncio
async def test_torrent_peers(client: APIClient):
    sample = make_torrent_single("sync_torrent_peers")

    async with temporary_torrents(client, sample):
        torrent_peers = await client.sync.torrent_peers(sample.hash)
        assert isinstance(torrent_peers, SyncTorrentPeers)
        assert isinstance(torrent_peers.rid, int)
