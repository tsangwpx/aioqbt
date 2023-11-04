from typing import Any, Collection, Mapping, Set, Tuple, Type, Union

import pytest
from helper.lang import retry_assert
from helper.torrent import make_torrent_single
from helper.webapi import temporary_torrents

from aioqbt.api import AddFormBuilder
from aioqbt.api.types import SyncMainData, SyncServerState, SyncTorrentPeers
from aioqbt.client import APIClient


def value_types(value: Any) -> Union[Set[Type[Any]], Set[Tuple[Type[Any], Type[Any]]]]:
    if isinstance(value, Mapping):
        return {(type(k), type(v)) for k, v in value.items()}
    elif isinstance(value, Collection):
        return {type(v) for v in value}
    else:
        return {type(value)}


@pytest.mark.asyncio
async def test_maindata(client: APIClient) -> None:
    # Types are examined for selected keys and fail the test to update annotations

    def assert_maindata(smd: SyncMainData) -> None:
        assert isinstance(smd, SyncMainData)

        # always exist due to default/default_factory
        assert isinstance(smd.rid, int)
        assert isinstance(smd.full_update, bool)
        assert isinstance(smd.server_state, dict)
        assert_server_state(smd.server_state)

        assert isinstance(smd.torrents, dict)
        assert isinstance(smd.torrents_removed, list)
        assert value_types(smd.torrents_removed) <= {str}

        assert isinstance(smd.categories, dict)
        assert value_types(smd.categories) <= {(str, dict)}
        assert isinstance(smd.categories_removed, list)
        assert value_types(smd.categories_removed) <= {str}

        assert isinstance(smd.tags, list)
        assert value_types(smd.tags) <= {str}
        assert isinstance(smd.tags_removed, list)
        assert value_types(smd.tags_removed) <= {str}

        assert isinstance(smd.trackers, dict)
        assert value_types(smd.trackers) <= {(str, list)}
        assert isinstance(smd.trackers_removed, list)
        assert value_types(smd.trackers_removed) <= {str}

    def assert_server_state(state: SyncServerState) -> None:
        if "connection_status" in state:
            assert state["connection_status"] in {"connected", "firewalled", "disconnected"}

    maindata = await client.sync.maindata()
    assert_maindata(maindata)

    category = "sync_maindata_category"
    tag = "sync_maindata_tag"
    tracker_url = "http://localhost/tracker"

    sample = make_torrent_single(
        "sync_maindata",
        {
            "announce": tracker_url,
        },
    )

    await client.torrents.add(
        AddFormBuilder.with_client(client)
        .category(category)
        .tags([tag])
        .include_file(sample.data)
        .build()
    )

    try:

        @retry_assert
        async def ready():
            torrents = await client.torrents.info(hashes=(sample.hash,))
            assert sample.hash in [s.hash for s in torrents]

        await ready()

        maindata2 = await client.sync.maindata(maindata.rid)
        assert_maindata(maindata2)
        assert maindata2.torrents

        await client.torrents.delete((sample.hash,), delete_files=True)

        maindata3 = await client.sync.maindata(maindata2.rid)
        assert_maindata(maindata3)
        assert maindata3.torrents_removed
    finally:
        await client.torrents.delete((sample.hash,), delete_files=True)


@pytest.mark.asyncio
async def test_torrent_peers(client: APIClient):
    sample = make_torrent_single("sync_torrent_peers")

    async with temporary_torrents(client, sample):
        torrent_peers = await client.sync.torrent_peers(sample.hash)
        assert isinstance(torrent_peers, SyncTorrentPeers)
        assert isinstance(torrent_peers.rid, int)
