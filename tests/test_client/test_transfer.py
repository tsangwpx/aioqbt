import pytest

from aioqbt.api.types import TransferInfo
from aioqbt.client import APIClient


@pytest.mark.asyncio
async def test_speed_limits_mode(client: APIClient):
    info = await client.transfer.info()
    assert isinstance(info, TransferInfo), info
    assert isinstance(repr(info), str)

    slm = await client.transfer.speed_limits_mode()
    assert slm in (0, 1), slm

    await client.transfer.set_speed_limits_mode(slm)
    assert slm == await client.transfer.speed_limits_mode()

    await client.transfer.set_speed_limits_mode(1 - slm)
    assert slm != await client.transfer.speed_limits_mode()

    await client.transfer.set_speed_limits_mode(slm)
    assert slm == await client.transfer.speed_limits_mode()


@pytest.mark.asyncio
async def test_upload_download_limits(client: APIClient):
    up_limit = 1024 * 3
    dl_limit = 1024 * 2

    up_limit_orig = await client.transfer.upload_limit()
    await client.transfer.set_upload_limit(up_limit)
    assert up_limit == await client.transfer.upload_limit()
    await client.transfer.set_upload_limit(up_limit_orig)
    assert up_limit_orig == await client.transfer.upload_limit()

    with pytest.raises(ValueError):
        await client.transfer.set_upload_limit(1)

    dl_limit_orig = await client.transfer.download_limit()
    await client.transfer.set_download_limit(dl_limit)
    assert dl_limit == await client.transfer.download_limit()
    await client.transfer.set_download_limit(dl_limit_orig)
    assert dl_limit_orig == await client.transfer.upload_limit()

    with pytest.raises(ValueError):
        await client.transfer.set_download_limit(1)


@pytest.mark.asyncio
async def test_ban_peers(client: APIClient):
    assert client.api_version is not None
    if client.api_version < (2, 3, 0):
        pytest.skip("ban_peers requires API v2.3.0")

    await client.transfer.ban_peers((("127.0.0.1", 80),))
