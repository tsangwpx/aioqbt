import pytest

from aioqbt.api.types import LogMessage, LogPeer
from aioqbt.client import APIClient


@pytest.mark.asyncio
async def test_log(client: APIClient):
    logs = await client.log.main()
    assert isinstance(logs, list)
    if logs:
        message = logs[0]
        assert isinstance(message, LogMessage)
        assert isinstance(message.id, int)

    peers = await client.log.peers()
    assert isinstance(peers, list)
    if peers:
        peer_log = peers[0]
        assert isinstance(peer_log, LogPeer)
        assert isinstance(peer_log.id, LogPeer)
