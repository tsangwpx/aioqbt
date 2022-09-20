from datetime import datetime, timedelta, timezone

import pytest

from aioqbt.chrono import TimeUnit
from aioqbt.converter import (
    DateTimeConverter,
    DurationConverter,
    EnumConverter,
    ScalarListConverter,
)

EPOCH = datetime.fromtimestamp(0)
NONE_TABLE = dict.fromkeys(
    (
        -1,
        0xFFFF_FFFF,  # u32(-1)
    )
)


def _fromtimestamp(ts: float, tz=None):
    if ts >= 0 or tz is not None:
        return datetime.fromtimestamp(ts, tz)
    else:
        return EPOCH + timedelta(seconds=ts)


def test_datetime():
    ts = 1662803940  # full moon
    tz = timezone(timedelta(hours=8))
    tz_ctx = {
        "timezone": tz,
    }

    conv = DateTimeConverter()
    assert conv(0, {}) == _fromtimestamp(0)
    assert conv(0, tz_ctx) == _fromtimestamp(0, tz)
    assert conv(ts, {}) == _fromtimestamp(ts)
    assert conv(-ts, {}) == _fromtimestamp(-ts)
    assert conv(-1, {}) == _fromtimestamp(-1)
    assert conv(-1, tz_ctx) == _fromtimestamp(-1, tz)

    conv = DateTimeConverter(NONE_TABLE)
    assert conv(0, {}) == _fromtimestamp(0)
    assert conv(0, tz_ctx) == _fromtimestamp(0, tz)
    assert conv(ts, {}) == _fromtimestamp(ts)
    assert conv(-ts, {}) == _fromtimestamp(-ts)
    assert conv(-1, {}) is None
    assert conv(-1, tz_ctx) is None


def test_duration():
    conv = DurationConverter(TimeUnit.SECONDS)
    assert conv(0, {}) == timedelta()
    assert conv(60, {}) == timedelta(minutes=1)
    assert conv(-60, {}) == timedelta(minutes=-1)
    assert conv(-1, {}) == timedelta(seconds=-1)

    conv = DurationConverter(TimeUnit.MINUTES)
    assert conv(0, {}) == timedelta()
    assert conv(1, {}) == timedelta(minutes=1)
    assert conv(-1, {}) == timedelta(minutes=-1)

    conv = DurationConverter(TimeUnit.SECONDS, NONE_TABLE)
    assert conv(0, {}) == timedelta()
    assert conv(60, {}) == timedelta(minutes=1)
    assert conv(-60, {}) == timedelta(minutes=-1)
    assert conv(-1, {}) is None

    conv = DurationConverter(TimeUnit.MINUTES, NONE_TABLE)
    assert conv(0, {}) == timedelta()
    assert conv(1, {}) == timedelta(minutes=1)
    assert conv(-1, {}) is None


def test_scalar_list():
    conv = ScalarListConverter(",")
    assert conv("", {}) == []
    assert conv("1", {}) == ["1"]
    assert conv("1,2,3", {}) == ["1", "2", "3"]
    assert conv(",1,", {}) == ["1"]

    conv = ScalarListConverter(",", int)
    assert conv("", {}) == []
    assert conv("1", {}) == [1]
    assert conv("1,2,3", {}) == [1, 2, 3]
    assert conv(",1,", {}) == [1]

    with pytest.raises(ValueError):
        ScalarListConverter("")


def test_enums():
    from aioqbt._compat import IntEnum

    class IntChoice(IntEnum):
        ONE = 1
        TWO = 2
        THREE = 3

    conv = EnumConverter(IntChoice)
    assert conv(1, {}) is IntChoice.ONE
    with pytest.raises(ValueError):
        conv(-999, {})

    with pytest.raises(TypeError):
        EnumConverter(object)  # type: ignore
