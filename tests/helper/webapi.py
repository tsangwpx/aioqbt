import contextlib
from typing import AsyncIterator, Dict, List

from helper.lang import busy_wait_for
from helper.torrent import TorrentData

from aioqbt.api import AddFormBuilder
from aioqbt.api.types import TorrentInfo
from aioqbt.client import APIClient


@contextlib.asynccontextmanager
async def temporary_torrents(
    client: APIClient,
    *samples: TorrentData,
    paused: bool = True,
) -> AsyncIterator[List[TorrentInfo]]:
    builder = AddFormBuilder.with_client(client)
    builder = builder.stopped(paused)

    table: Dict[str, int] = {}
    for i, item in enumerate(samples):
        table[item.hash] = i
        builder = builder.include_file(item.data, f"{item.name}.torrent")

    hashes = list(table.keys())
    torrents = []

    if hashes:
        await client.torrents.add(builder.build())

        async def cond_added() -> bool:
            nonlocal torrents
            torrents = await client.torrents.info(hashes=hashes)
            return len(torrents) == len(hashes)

        success = await busy_wait_for(cond_added)
        assert success, f"Failed to add {len(samples)} torrents: {samples[0].name}"

    try:
        yield torrents
    finally:
        if hashes:
            await client.torrents.delete(hashes, True)
