from enum import Enum
from typing import NewType

Seconds = NewType("Seconds", int)
Minutes = NewType("Minutes", int)


class TimeUnit(Enum):
    """
    TimeUnit enum.

    Conversion helper between time units
    """

    NANOSECONDS = 1
    MICROSECONDS = 1_000
    MILLISECONDS = 1_000_000
    SECONDS = 1_000_000_000
    MINUTES = 1_000_000_000 * 60
    HOURS = 1_000_000_000 * 3600
    DAYS = 1_000_000_000 * 86400

    def from_duration(self, d: float, unit: "TimeUnit") -> float:
        """Convert value from the given unit to the self unit (float)"""
        return d * unit._value_ / self._value_

    def from_duration_int(self, d: int, unit: "TimeUnit") -> int:
        """Convert value from the given unit to the self unit (int)"""
        return d * unit._value_ // self._value_

    def from_nanos(self, d: float) -> float:
        """Convert nanoseconds to self unit"""
        return d * TimeUnit.NANOSECONDS._value_ / self._value_

    def from_micros(self, d: float) -> float:
        """Convert microseconds to self unit"""
        return d * TimeUnit.MICROSECONDS._value_ / self._value_

    def from_millis(self, d: float) -> float:
        """Convert milliseconds to self unit"""
        return d * TimeUnit.MILLISECONDS._value_ / self._value_

    def from_seconds(self, d: float) -> float:
        """Convert seconds to self unit"""
        return d * TimeUnit.SECONDS._value_ / self._value_

    def from_minutes(self, d: float) -> float:
        """Convert minutes to self unit"""
        return d * TimeUnit.MINUTES._value_ / self._value_

    def from_hours(self, d: float) -> float:
        """Convert hours to self unit"""
        return d * TimeUnit.HOURS._value_ / self._value_

    def from_days(self, d: float) -> float:
        """Convert days to self unit"""
        return d * TimeUnit.DAYS._value_ / self._value_

    @classmethod
    def convert(cls, d: float, src: "TimeUnit", dst: "TimeUnit") -> float:
        """Convert a numeric duration in some unit to one in another."""
        return dst.from_duration(d, src)
