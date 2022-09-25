import sys
from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping, Optional, Type, TypeVar

from aioqbt._compat import StrEnum
from aioqbt.chrono import TimeUnit

__all__ = (
    "Converter",
    "NegativeMode",
    "DateTimeConverter",
    "DurationConverter",
    "EnumConverter",
    "ScalarListConverter",
)

E = TypeVar("E", bound=Enum)
_FROZEN_DICT: Mapping[Any, Any] = MappingProxyType({})


class Converter(metaclass=ABCMeta):
    """
    Convert json.decode() result to objects.
    """

    @abstractmethod
    def __call__(self, value: Any, context: Mapping[Any, Any]) -> Any:
        raise NotImplementedError


class NegativeMode(StrEnum):
    """
    Behavior when negative numbers are encountered.
    """

    ERROR = "error"  # raise
    CONVERT = "convert"  # convert negative values as well


def _find_timezone():
    """Find local timezone"""
    # https://stackoverflow.com/a/39079819/1692260
    return datetime.now(timezone.utc).astimezone().tzinfo


_TIMEZONE = _find_timezone()
_EPOCH = datetime.fromtimestamp(0)


class DateTimeConverter(Converter):
    """
    Convert Unix timestamp to ``datetime`` object.

    .. note::
        Some attributes are roughly the same except special cases.
        - :attr:`.TorrentInfo.added_on` and :attr:`.TorrentProperties.addition_date`.
            They are set when the corresponding torrents are added and supposedly available.
        - :attr:`.TorrentInfo.seen_complete` and :attr:`.TorrentProperties.last_seen`.
            :attr:`.TorrentInfo.completion_on` and :attr:`.TorrentProperties.completion_date`.
            These attributes are directly exposed in :class:`.TorrentInfo`
            while the counterparts return invalid values as ``-1`` in
            :class:`.TorrentProperties`.

    .. note::
        Some input values are special or malformed.
        ``-1`` usually indicate the absence of value.
        In some versions, ``0xFFFF_FFFF`` may be returned because of
        the 32-bit unsigned value of ``-1``.
        However, :attr:`.TorrentProperties.creation_date` is directly
        returned regardless of its validity.
        When its value is undefined (usually represented as zero), the
        returned value usually offsets by time zone
        (e.g. ``-28800`` for UTC+8, ``28800`` for UTC-8).
    """

    # Static mappings
    _table: Mapping[int, Any]

    def __init__(self, table: Optional[Mapping[int, Any]] = None):
        super().__init__()

        if table is None:
            table = _FROZEN_DICT

        self._table = table

    def __call__(self, value: Any, context: Mapping[Any, Any]) -> Any:
        if value in self._table:
            return self._table[value]

        tz = context.get("timezone")

        if value < 0 and tz is None and sys.platform.startswith("win32"):
            # On Windows, negative timestamp without timezone may cause error
            # https://github.com/python/cpython/issues/80620#issue-1199008790
            epoch = datetime.fromtimestamp(0)
            return epoch + timedelta(seconds=value)
        else:
            return datetime.fromtimestamp(value, tz)


class DurationConverter(Converter):
    """
    Convert number to timedelta.
    """

    def __init__(self, unit: TimeUnit, table: Optional[Mapping[int, Any]] = None):
        """
        :param unit: input unit
        :param table: optional special mappings
        """
        super().__init__()

        if table is None:
            table = _FROZEN_DICT

        self._unit = unit
        self._table = table

    def __call__(self, value: Any, context: Mapping[Any, Any]) -> Any:
        if value in self._table:
            return self._table[value]

        value = TimeUnit.SECONDS.from_duration(value, self._unit)
        delta = timedelta(seconds=value)
        return delta


class ScalarListConverter(Converter):
    """
    Split string into list.

    An input string is split with a separator. Empty items are discarded.
    An optional function ``cast`` may be provided to transform items.
    """

    def __init__(self, sep: str, cast: Optional[Callable[[str], Any]] = None):
        super().__init__()

        if not sep:
            raise ValueError("sep must not be empty")

        self._sep = sep
        self._cast = cast

    def __call__(self, value: Any, context: Mapping[Any, Any]) -> Any:
        items = value.split(self._sep)
        cast = self._cast

        if cast is None:
            return [s for s in items if s]
        else:
            return [cast(s) for s in items if s]


class EnumConverter(Converter):
    """
    Convert values to members of enums.
    """

    def __init__(self, enum_type: Type[E]):
        super().__init__()

        if not issubclass(enum_type, Enum):
            raise TypeError(f"expects a subclass of Enum: {enum_type!r}")

        self._enum_type = enum_type

    def __call__(self, value: Any, context: Mapping[Any, Any]) -> Any:
        try:
            return self._enum_type(value)
        except ValueError:
            raise ValueError(f"{self._enum_type} has no such value: {value!r}") from None
