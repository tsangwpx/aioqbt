import pytest

from aioqbt.bittorrent import get_info_hash


def test_get_info_hash():
    info_hash = "0" * 40
    bin_hash = b"\x00" * 20

    assert get_info_hash(info_hash) == info_hash
    assert get_info_hash(bin_hash) == info_hash

    with pytest.raises(ValueError):
        get_info_hash("0" * 20)

    with pytest.raises(ValueError):
        get_info_hash("z" * 40)
