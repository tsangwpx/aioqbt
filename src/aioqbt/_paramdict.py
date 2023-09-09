import os
import re
from datetime import timedelta
from math import isfinite
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    TypeVar,
    Union,
)

from aioqbt.bittorrent import InfoHash, InfoHashes, InfoHashesOrAll, get_info_hash
from aioqbt.chrono import TimeUnit
from aioqbt.typing import StrPath

T = TypeVar("T")
PrepareFn = Callable[[T], Union[float, str]]

_CAMEL_PATTERN = re.compile(r"(?!^)([A-Z]+)", re.ASCII)


def _camel2snake(name: str) -> str:
    """
    Convert camelCase to snake_case

    Examples:
    - helloWorld -> hello_world
    - SendHTTP -> send_http
    - HTTPRequest -> httprequest
    - HTTP2Request -> http2_request
    - seedingTimeLimit -> seeding_time_limit
    """
    return _CAMEL_PATTERN.sub(lambda m: f"_{m.group(1).lower()}", name).lower()


def _param_name(key: str, param: Optional[str]) -> str:
    """
    Derive parameter name from key name
    """

    if param is None:
        return _camel2snake(key)
    else:
        return param


def _missing():
    raise AssertionError


class ParamDict(MutableMapping[str, str]):
    """
    A helper dict to construct GET params and POST data in common pattern
    """

    _data: Dict[str, str]

    def __init__(
        self,
        data: Optional[Mapping[str, Any]] = None,
    ):
        if data is None:
            self._data = {}
        elif isinstance(data, ParamDict):
            self._data = data._data.copy()
        else:
            self._data = {}

            for k, v in list(data.items()):
                self.put(k, v)

    def __setitem__(self, key: str, value: str):
        self._data[key] = value

    def __delitem__(self, key: str):
        del self._data[key]

    def __getitem__(self, key: str) -> str:
        return self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __deepcopy__(self, memo=None):
        return type(self)(self)

    __copy__ = __deepcopy__

    @classmethod
    def _missing_param(cls, key: str, param: Optional[str]):
        return TypeError(f"{_param_name(key, param)!r} is required")

    def to_dict(self) -> Dict[str, str]:
        return self._data.copy()

    def _put(
        self,
        key: str,
        param: Optional[str],
        value: Any,
        optional: bool,
        prepare: Optional[PrepareFn[Any]] = None,
        default: Any = _missing,
    ):
        """
        Associate a key with a value

        The put operation is ignored if the value is None and optional is True.
        An exception is raised if the value is None but optional is False.

        :param key: the key name.
        :param value: the value or None if empty.
        :param param: the parameter name.
        :param optional: whether value None is allowed.
        :param prepare: callable to convert non-None value to str, int, or float
        :param default: default value if value is None.
        """
        if value is None:
            if default is _missing:
                if optional:
                    return

                raise self._missing_param(key, param)

            value = default

        if prepare is None:
            if not isinstance(value, (str, int, float)):
                raise TypeError(
                    f"{_param_name(key, param)!r} expect"
                    f" str, int, or float instead of {type(value)}"
                )

            value = str(value)
        else:
            value = prepare(value)

            if not isinstance(value, (str, int, float)):
                raise TypeError(
                    f"{_param_name(key, param)!r} expect {prepare} result in"
                    f" str, int, or float instead of {type(value)}"
                )

            value = str(value)

        self._data[key] = value

    def put(
        self,
        key: str,
        value: Any,
        *,
        param: Optional[str] = None,
        optional: bool = False,
        prepare: Optional[PrepareFn[Any]] = None,
        default: Any = _missing,
    ):
        self._put(key, param, value, optional, prepare, default)

    def optional_str(self, key: str, value: Optional[str], *, param: Optional[str] = None):
        self._put(key, param, value, True, str)

    def required_str(self, key: str, value: str, *, param: Optional[str] = None):
        self._put(key, param, value, False, str)

    def optional_int(self, key: str, value: Optional[int], *, param: Optional[str] = None):
        self._put(key, param, value, True, int)

    def required_int(self, key: str, value: int, *, param: Optional[str] = None):
        self._put(key, param, value, False, int)

    def optional_float(self, key: str, value: Optional[float], *, param: Optional[str] = None):
        self._put(key, param, value, True, float)

    def required_float(self, key: str, value: float, *, param: Optional[str] = None):
        self._put(key, param, value, False, float)

    def optional_bool(self, key: str, value: Optional[bool], *, param: Optional[str] = None):
        self._put(key, param, value, True, _prepare_bool)

    def required_bool(self, key: str, value: bool, *, param: Optional[str] = None):
        self._put(key, param, value, False, _prepare_bool)

    def _put_duration(
        self,
        key: str,
        param: Optional[str],
        value: Union[timedelta, int, float, None],
        unit: TimeUnit,
        optional: bool,
    ):
        if isinstance(value, timedelta):
            value = unit.from_seconds(value.total_seconds())

        if isinstance(value, float) and not isfinite(value):
            raise ValueError(f"{_param_name(key, param)!r} expect a finite value: {value!r}")

        self._put(key, param, value, optional, int)

    def required_duration(
        self,
        key: str,
        value: Union[timedelta, int, float],
        unit: TimeUnit,
        *,
        param: Optional[str] = None,
    ):
        self._put_duration(key, param, value, unit, False)

    def optional_duration(
        self,
        key: str,
        value: Union[timedelta, int, float, None],
        unit: TimeUnit,
        *,
        param: Optional[str] = None,
    ):
        self._put_duration(key, param, value, unit, True)

    def required_path(
        self,
        key: str,
        value: StrPath,
        *,
        param: Optional[str] = None,
    ):
        self._put(key, param, value, False, _prepare_path)

    def optional_path(
        self,
        key: str,
        value: Optional[StrPath],
        *,
        param: Optional[str] = None,
    ):
        self._put(key, param, value, True, _prepare_path)

    def _put_list(
        self,
        key: str,
        value: Optional[Iterable[T]],
        sep: str,
        param: Optional[str],
        optional: bool,
        prepare: Optional[PrepareFn[T]],
        nonempty: bool,
    ):
        if value is None:
            if optional:
                return

            raise self._missing_param(key, param)

        if prepare is None:
            items = [str(s) for s in value]
        else:
            items = [str(prepare(s)) for s in value]

        if nonempty and not items:
            raise ValueError(f"{_param_name(key, param)!r} must not be empty")

        self._data[key] = sep.join(items)

    def required_list(
        self,
        key: str,
        value: Iterable[T],
        sep: str,
        *,
        param: Optional[str] = None,
        prepare: Optional[PrepareFn[T]] = None,
        nonempty: bool = False,
    ):
        self._put_list(key, value, sep, param, False, prepare, nonempty)

    def optional_list(
        self,
        key: str,
        value: Optional[Iterable[T]],
        sep: str,
        *,
        param: Optional[str] = None,
        prepare: Optional[PrepareFn[T]] = None,
        nonempty: bool = False,
    ):
        self._put_list(key, value, sep, param, True, prepare, nonempty)

    @classmethod
    def with_hash(
        cls,
        hash: InfoHash,
        *,
        key: Optional[str] = None,
        param: Optional[str] = None,
    ):
        if key is None:
            key = "hash"

        res = cls()
        res.put(key, hash, param=param, prepare=get_info_hash)
        return res

    @classmethod
    def with_hashes(
        cls,
        hashes: InfoHashes,
        *,
        key: Optional[str] = None,
        param: Optional[str] = None,
        nonempty: bool = False,
    ):
        if key is None:
            key = "hashes"

        res = cls()
        res.required_list(key, hashes, "|", param=param, prepare=get_info_hash, nonempty=nonempty)
        return res

    @classmethod
    def with_hashes_or_all(
        cls,
        hashes: InfoHashesOrAll,
        *,
        key: Optional[str] = None,
        param: Optional[str] = None,
        nonempty: bool = False,
    ):
        if key is None:
            key = "hashes"

        res = cls()
        if hashes == "all":
            res.put(key, "all", param=param)
        else:
            res.required_list(
                key,
                hashes,
                "|",
                param=param,
                prepare=get_info_hash,
                nonempty=nonempty,
            )
        return res


def _prepare_bool(b: bool) -> str:
    """
    Convert boolean values to "true" or "false" string in lowercase
    """
    return "true" if bool(b) else "false"


def _prepare_path(p: StrPath) -> str:
    """
    Convert path-like object to str
    """
    return os.fsdecode(p).replace("\\", "/")
