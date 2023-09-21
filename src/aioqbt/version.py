import re
from functools import total_ordering
from typing import Any, NamedTuple, Optional, Tuple, Union

from typing_extensions import Protocol, Self

from aioqbt.exc import VersionError

__all__ = (
    "ClientVersion",
    "APIVersion",
)

_VERSION_PATTERN = re.compile(
    r"^v?(\d+)\.(\d+)(?:\.(\d+)(?:\.(\d+))?)?((?:alpha|beta|rc)\d*)?$",
    re.IGNORECASE,
)

_API_VERSION_PATTERN = re.compile(
    r"^(\d+)\.(\d+)(?:\.(\d+))?$",
    re.IGNORECASE,
)


@total_ordering
class ClientVersion:
    """
    Represent client version.
    """

    _key: Tuple[int, int, int, int, str, int]
    _status: str

    def __init__(self, major: int, minor: int, patch: int, build: int = 0, status: str = ""):
        st0, st1 = self._parse_status(status)
        self._key = (major, minor, patch, build, st0, st1)
        self._status = status

    @property
    def major(self) -> int:
        """Major number."""
        return self._key[0]

    @property
    def minor(self) -> int:
        """Minor number."""
        return self._key[1]

    @property
    def patch(self) -> int:
        """Patch number."""
        return self._key[2]

    @property
    def build(self) -> int:
        """Build number."""
        return self._key[3]

    @property
    def status(self) -> str:
        """Status string."""
        return self._status

    def __eq__(self, other):
        if isinstance(other, ClientVersion):
            return self._key == other._key
        return NotImplemented

    def __hash__(self):
        return hash(self._key)

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, ClientVersion):
            return self._key < other._key
        return NotImplemented

    def __str__(self):
        result = f"{self.major:d}.{self.minor:d}.{self.patch:d}"

        if self.build != 0:
            result += f".{self.build:d}"

        result += self.status
        return result

    @classmethod
    def _parse_status(cls, status: str) -> Tuple[str, int]:
        if status == "":
            return "release", 0

        match = re.match(r"(alpha|beta|rc)(\d*)", status, re.IGNORECASE)
        if match is None:
            raise ValueError(f"Bad status: {status!r}")
        a, b = match.groups()
        return a.lower(), int(b or 0)

    @classmethod
    def parse(cls, version: str) -> "ClientVersion":
        """
        Parse client version.

        Format::

            major.minor.patch[.build][status]

        Examples::

            4.2.5
            4.4.0beta2
            4.4.3.1
        """

        match = _VERSION_PATTERN.match(version)
        if match is None:
            raise ValueError(f"Bad version: {version!r}")

        major = int(match[1])
        minor = int(match[2])
        patch = int(match[3] or 0)
        build = int(match[4] or 0)
        status = match[5] or ""
        return cls(major, minor, patch, build, status)


class APIVersion(NamedTuple):
    """
    Represent API version.

    Instances can also be compared with 3-tuple of :class:`int`.

    """

    major: int
    """Major number."""

    minor: int
    """Minor number."""

    release: int = 0
    """Release number."""

    @classmethod
    def parse(cls, version: str) -> "APIVersion":
        """
        Parse API version.

        Format::

            major.minor[.release]

        where ``major``, ``minor`` and ``release`` are all digits.
        """
        match = _API_VERSION_PATTERN.match(version)

        if match is None:
            raise ValueError(f"Bad API version: {version!r}")

        s1, s2, s3 = match.groups()

        return cls(int(s1), int(s2), int(s3 or 0))

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.release}"

    @classmethod
    def compare(
        cls,
        a: Optional[Union[Self, Tuple[int, int, int]]],
        b: Optional[Union[Self, Tuple[int, int, int]]],
    ) -> int:
        """
        Compare two API versions.

        Return zero if ``a == b``; a negative value if ``a < b``;
        or a positive value if ``a > b``.

        ``None`` is a special value treated as the latest version.

        :return: integer value indicating version relationship.
        """

        if a is None:
            if b is None:
                return 0
            else:
                return 1
        elif b is None:
            return -1
        elif a == b:
            return 0
        elif a < b:
            return -1
        else:
            return 1


class Comparable(Protocol):
    def __eq__(self, other):
        pass

    def __ne__(self, other):
        pass

    def __lt__(self, other):
        pass

    def __le__(self, other):
        pass

    def __gt__(self, other):
        pass

    def __ge__(self, other):
        pass


def version_satisfy(version: Optional[Comparable], minimum: Comparable) -> bool:
    """
    Compare version with minimum requirement and return boolean

    :param version: current version, or ``None`` as the latest
    :param minimum: minimum version
    """
    return version is None or version >= minimum


def version_check(version: Optional[Comparable], minimum: Comparable):
    """
    Compare version with minimum requirement and raise if violated.

    :param version: current version, or ``None`` as the latest
    :param minimum: minimum version
    """
    if version is not None and version < minimum:
        raise VersionError(f"Version {minimum} is required but {version} is found")


def param_version_check(param, version: Optional[Comparable], minimum: Comparable):
    if not version_satisfy(version, minimum):
        if type(minimum) is tuple:
            minimum = type(version)(*minimum)  # type: ignore

        raise VersionError(f"{param!r} requires version {version!r} but {minimum!r} found")
