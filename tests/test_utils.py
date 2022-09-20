import pytest

from aioqbt.chrono import TimeUnit


def test_timeunit():
    assert TimeUnit.NANOSECONDS.from_nanos(1) == 1
    assert TimeUnit.NANOSECONDS.from_micros(1) == 1000
    assert TimeUnit.NANOSECONDS.from_millis(1) == 1_000_000
    assert TimeUnit.NANOSECONDS.from_seconds(1) == 1_000_000_000
    assert TimeUnit.SECONDS.from_seconds(1) == 1
    assert TimeUnit.SECONDS.from_minutes(1) == 60
    assert TimeUnit.SECONDS.from_hours(1) == 3600
    assert TimeUnit.SECONDS.from_days(1) == 86400

    assert TimeUnit.SECONDS.from_millis(500) == pytest.approx(0.5)
    assert TimeUnit.SECONDS.from_duration(500, TimeUnit.MILLISECONDS) == pytest.approx(0.5)

    assert TimeUnit.convert(60, TimeUnit.SECONDS, TimeUnit.MINUTES) == 1

    assert TimeUnit.MINUTES.from_duration_int(119, TimeUnit.SECONDS) == 1
