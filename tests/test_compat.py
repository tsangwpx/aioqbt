from enum import Enum

from aioqbt._compat import repr_enum
from aioqbt.api.types import FilePriority, PieceState, TorrentState


def test_repr_enum():
    @repr_enum
    class StrEnum(str, Enum):
        pass

    class Strings(StrEnum):
        HELLO = "hello"

    assert str(Strings.HELLO) == "hello"

    @repr_enum
    class IntEnum(int, Enum):
        pass

    class Numbers(IntEnum):
        ONE = 1

    assert str(Numbers.ONE) == "1"


def check_enum(cls):
    for name, member in cls.__members__.items():
        assert str(member) == str(member._value_), repr(member)


def test_api_enums():
    enum_types = (
        TorrentState,
        PieceState,
        FilePriority,
    )

    for cls in enum_types:
        check_enum(cls)
