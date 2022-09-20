from typing import Iterable, Union

from typing_extensions import Literal

InfoHash = Union[str, bytes]
InfoHashes = Iterable[InfoHash]
InfoHashesOrAll = Union[InfoHashes, Literal["all"]]


def get_info_hash(obj: InfoHash) -> str:
    """Get info hash"""

    if isinstance(obj, (bytes, bytearray, memoryview)):
        obj = obj.hex()

    if len(obj) != 40 and len(obj) != 64:
        raise ValueError("info hash is a hexadecimal string of 40 or 60 characters")

    try:
        int(obj, 16)
    except ValueError:
        raise ValueError("info hash is a hexadecimal string of 40 or 60 characters")

    return obj
