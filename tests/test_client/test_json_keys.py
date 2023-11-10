"""

This module is used to detect new keys from JSON response

Rough steps:
1. Redefine some fixture to module scope
2. Use a memo object to store API type and its data
3a. For @declarative, ObjectMapperProxy will feed memo data
3b. For TypedDict, feed data manually
4. Comparing type annotations and its data received

Currently,
- New fields are reported in both @declarative types and TypedDict.
- Incompatible types are reported only in TypedDict.

"""

import asyncio
import collections
import dataclasses
import enum
import os
import warnings
from typing import (
    Any,
    AsyncIterator,
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
)

import pytest
import pytest_asyncio
from helper.client import LoginInfo, client_context
from helper.torrent import TorrentData, make_torrent_files, make_torrent_single
from helper.webapi import temporary_torrents
from typing_extensions import Literal, get_args, get_origin, get_type_hints, is_typeddict

from aioqbt import api
from aioqbt.client import APIClient
from aioqbt.mapper import ATTR_TYPE_INFO, ObjectMapper, _TypeInfo
from aioqbt.version import APIVersion

T = TypeVar("T")

_SELECTED_TYPES = [
    # app
    api.BuildInfo,
    api.Preferences,
    api.NetworkInterface,
    # torrents
    api.TorrentInfo,
    api.TorrentProperties,
    api.Tracker,
    api.WebSeed,
    api.FileEntry,
    api.Category,
    # log
    api.LogMessage,
    api.LogPeer,
    # sync
    api.SyncTorrentInfo,
    api.SyncCategory,
    api.SyncServerState,
    api.SyncMainData,
    # api.SyncPeer,
    api.SyncTorrentPeers,
    # transfer
    api.TorrentInfo,
    # RSS
    api.RSSRule,
    # api.RSSArticle,
    # api.RSSFolder,
    # api.RSSFeed,
    # Search omitted
]


class Memo:
    _data: DefaultDict[Type[Any], List[Dict[str, Any]]]

    def __init__(self) -> None:
        self._data = collections.defaultdict(list)

    def add(self, cls: Type[Any], sample: Any) -> None:
        # use Any to accept TypedDict and Dict
        assert isinstance(sample, dict), type(sample)
        self._data[cls].append(sample)

    def add_many(self, cls: Type[Any], samples: Iterable[Any]) -> None:
        # use Any to accept TypedDict and Dict
        samples = list(samples)
        assert all(isinstance(s, dict) for s in samples), {type(s) for s in samples}
        self._data[cls].extend(samples)

    def collect(self, cls: Type[Any]) -> Optional[Dict[str, List[Any]]]:
        samples = self._data.get(cls)
        if samples is None:
            return None

        result = collections.defaultdict(list)
        for entry in samples:
            for key, value in entry.items():
                result[key].append(value)

        return dict(result)


class ObjectMapperProxy(ObjectMapper):
    def __init__(self, mapper: ObjectMapper, memo: Memo) -> None:
        self.__mapper = mapper
        self.__memo = memo

    def create_object(
        self,
        rtype: Type[T],
        data: Mapping[str, Any],
        context: Mapping[Any, Any],
    ) -> T:
        self.__memo.add(rtype, dict(data))
        return self.__mapper.create_object(rtype, data, context)


@pytest.fixture(scope="module")
def warn_missing_keys() -> bool:
    try:
        return int(os.environ["WARN_MISSING_KEYS"]) == 1
    except (ValueError, KeyError, TypeError):
        return False


@pytest.fixture(scope="module")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def samples() -> List[TorrentData]:
    base = {
        "announce": "http://localhost/tracker",
        "url-list": ["http://localhost/data/"],
    }
    sample_single = make_torrent_single("api_types_single", base)
    sample_files = make_torrent_files("api_types_files", base)
    return [sample_single, sample_files]


@pytest.fixture(scope="module")
def memo() -> Memo:
    return Memo()


@pytest_asyncio.fixture(scope="module")
async def client(
    mock_login: LoginInfo,
    client_cookies: List[Any],
    memo: Memo,
) -> AsyncIterator[APIClient]:
    """
    client in module scope, and store traffic to registry by proxy
    """
    client: APIClient

    async with client_context(mock_login, client_cookies) as client:
        client._mapper = ObjectMapperProxy(client._mapper, memo)
        yield client


@pytest_asyncio.fixture(scope="module")
async def activities(
    memo: Memo,
    client: APIClient,
    samples: List[TorrentData],
) -> None:
    """
    Do some activities here
    """

    hashes = [s.hash for s in samples]
    category = "test_api_types"
    rss_rule_name = "json_keys_rule"
    await client.torrents.create_category(category, "")

    async with temporary_torrents(client, *samples):
        if APIVersion.compare(client.api_version, (2, 3, 0)) >= 0:
            await client.app.build_info()
            await client.app.network_interface_list()

        await client.torrents.info(hashes=hashes)

        for hash_ in hashes:
            await client.torrents.properties(hash_)
            await client.torrents.trackers(hash_)
            await client.torrents.webseeds(hash_)
            await client.torrents.files(hash_)

        await client.torrents.categories()

        await client.transfer.info()

        await client.sync.maindata()

        for hash_ in hashes:
            await client.sync.torrent_peers(hash_)

        await client.log.main()
        await client.log.peers()

        memo.add(api.Preferences, await client.app.preferences())

        maindata = await client.sync.maindata()
        memo.add_many(api.SyncTorrentInfo, maindata.torrents.values())
        memo.add_many(api.SyncCategory, maindata.categories.values())
        memo.add(api.SyncServerState, maindata.server_state)

    await client.torrents.remove_categories([category])

    await client.rss.set_rule(rss_rule_name, api.RSSRule())
    rss_rules = await client.rss.rules()
    memo.add_many(api.RSSRule, rss_rules.values())
    await client.rss.remove_rule(rss_rule_name)


def _find_declarative_types() -> List[Type[Any]]:
    return [
        value
        for value in _SELECTED_TYPES
        if isinstance(value, type) and hasattr(value, ATTR_TYPE_INFO)
    ]


def _report_keys(cls: Type[Any], title: str, key: Iterable[str]):
    classname = cls.__name__
    msg = ", ".join(f"{s}" for s in sorted(key))
    warnings.warn(f"{title} keys in {classname}: {msg}")


@pytest.mark.asyncio
@pytest.mark.parametrize("cls", _find_declarative_types())
async def test_find_unknown_attrs(
    cls: Type[T],
    memo: Memo,
    activities: None,
    warn_missing_keys: bool,
) -> None:
    """check @declarative types"""
    collected = memo.collect(cls)
    if collected is None:
        pytest.xfail("nothing collected")

    assert dataclasses.is_dataclass(cls), cls

    try:
        type_info: _TypeInfo[T] = getattr(cls, ATTR_TYPE_INFO)
    except AttributeError:
        pytest.fail("missing type info")

    annotations = get_type_hints(cls)
    # check keys recognized by mapper
    annotations = {k: annotations[k] for k in type_info.fields.keys()}
    expected: Set[str] = set(annotations.keys())
    found: Set[str] = set(collected.keys())
    unknown = found - expected
    missing = expected - found

    # remove missing keys associated with default or default_factory
    missing.difference_update(type_info.default_fields)

    if unknown:
        _report_keys(cls, "unknown", unknown)

    if warn_missing_keys and missing:
        _report_keys(cls, "missing", missing)


def _find_typed_dict_types() -> List[Type[Any]]:
    return [value for value in _SELECTED_TYPES if is_typeddict(value)]


def _json_types(annotation: Any) -> Set[Type[Any]]:
    """
    return a set of possible Python types which JSON may be decoded into.
    Also see test_json_types() below
    """

    if isinstance(annotation, type):
        if annotation is float:
            return {float, int}
        elif annotation in (bool, int, str, list, dict, type(None)):
            return {annotation}
        elif issubclass(annotation, enum.Enum):
            if issubclass(annotation, int):
                return {int}
            elif issubclass(annotation, str):
                return {str}
            else:
                raise ValueError(f"Cannot coerce Enum {annotation} into JSON types")
        elif is_typeddict(annotation):
            # TypedDict runtime type is dict
            return {dict}

        raise ValueError(annotation)

    tp_origin = get_origin(annotation)
    tp_args = get_args(annotation)
    if isinstance(tp_origin, type):
        return _json_types(tp_origin)
    elif tp_origin == Literal:
        result = set()
        for arg in tp_args:
            result.update(_json_types(type(arg)))
        return result
    elif tp_origin == Union:
        result = set()
        for arg in tp_args:
            result.update(_json_types(arg))
        return result

    raise ValueError(annotation)


@pytest.mark.parametrize(
    "annotation,expected",
    [
        (str, {str}),
        (float, {int, float}),
        (int, {int}),
        (dict, {dict}),
        (list, {list}),
        (bool, {bool}),
        (None, {type(None)}),
        (Literal["aaa"], {str}),
        (Union[str, int], {str, int}),
        (api.TorrentState, {str}),
        (api.FilePriority, {int}),
    ],
)
def test_json_types(annotation: Any, expected: Set[Type[Any]]) -> None:
    """
    annotation := type(input)
    output := jsons.loads(json.dumps(input))
    expected := type(output)
    """

    def dummy(arg: Any) -> None:
        pass

    dummy.__annotations__["arg"] = annotation
    annotation = get_type_hints(dummy)["arg"]
    assert _json_types(annotation) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("cls", _find_typed_dict_types())
async def test_find_unknown_keys(
    cls: Type[T],
    memo: Memo,
    activities: None,
    warn_missing_keys: bool,
) -> None:
    """check TypedDict types"""

    collected = memo.collect(cls)
    if collected is None:
        pytest.xfail("nothing collected")

    assert is_typeddict(cls), cls
    annotations = get_type_hints(cls)
    expected: Set[str] = set(annotations.keys())
    found: Set[str] = set(collected.keys())
    unknown = found - expected
    missing = expected - found

    if unknown:
        _report_keys(cls, "unknown", unknown)

    if warn_missing_keys and missing:
        _report_keys(cls, "missing", missing)

    for key in expected.intersection(found):
        field_annotation = annotations[key]
        try:
            field_types = _json_types(field_annotation)
        except ValueError:
            msg = f"{cls.__name__}.{key} has unexpected annotation: {field_annotation!r}"
            pytest.fail(msg)

        sample_types = {type(s) for s in collected[key]}
        unknown_types = sample_types - field_types
        if unknown_types:
            example = next(s for s in collected[key] if type(s) in unknown_types)
            msg = (
                f"{cls.__name__}.{key} ({field_annotation}) received unknown types:"
                f" {unknown_types}; example={example!r}"
            )

            warnings.warn(msg)
