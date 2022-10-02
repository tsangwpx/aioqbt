import copy
import math
from datetime import timedelta
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

import pytest

from aioqbt._paramdict import ParamDict
from aioqbt.chrono import TimeUnit


def test_init():
    pd = ParamDict()
    assert pd.to_dict() == {}

    data = {
        "int": 1,
        "float": 1.5,
        "str": "hello",
    }
    pd = ParamDict(data)
    expected = {
        "int": "1",
        "float": "1.5",
        "str": "hello",
    }
    assert pd.to_dict() == expected

    pd2 = ParamDict(pd)
    assert pd == pd2
    assert pd2.to_dict() == expected

    data = {
        "a": "b",
        "b": "c",
    }
    pd = ParamDict(data)
    pd["hello"] = "world"
    assert pd["hello"] == "world"

    del pd["hello"]
    with pytest.raises(KeyError):
        _ = pd["hello"]

    assert len(pd) == 2
    assert "hello" not in pd

    pd3 = copy.copy(pd)
    assert pd3 == pd


def test_hash_factories():
    hash = "0" * 40

    pd = ParamDict.with_hash(hash)
    assert pd == {
        "hash": hash,
    }

    hashes = [
        "0" * 40,
        "1" * 40,
    ]
    pd = ParamDict.with_hashes(hashes)
    assert pd == {
        "hashes": "|".join(hashes),
    }

    pd = ParamDict.with_hashes_or_all("all")
    assert pd == {
        "hashes": "all",
    }


def test_param_names():
    pd = ParamDict()

    # test camel2snake
    with pytest.raises(TypeError, match="save_path"):
        pd.put("savePath", None)

    # test custom name
    with pytest.raises(TypeError, match="custom"):
        pd.put("savePath", None, param="custom")


def test_put():
    pd = ParamDict()
    assert len(pd) == 0

    pd.put("key", "value")
    assert pd["key"] == "value"
    assert len(pd) == 1

    pd.put("default", None, default="value2")
    assert pd["default"] == "value2"
    assert len(pd) == 2

    pd.put("optional", None, optional=True)
    assert "optional" not in pd
    assert len(pd) == 2

    with pytest.raises(TypeError):
        pd.put("required", None)

    pd.put("str", "str")
    pd.put("int", 123456)
    pd.put("float", 3.14)
    assert len(pd) == 5
    assert pd["str"] == "str"
    assert pd["int"] == "123456"
    assert pd["float"] == "3.14"

    with pytest.raises(TypeError):
        pd.put("unexpected_type", timedelta(seconds=123))

    pd.put("duration", timedelta(seconds=456), prepare=timedelta.total_seconds)

    def bad_prepare(s) -> Any:
        return None

    with pytest.raises(TypeError):
        pd.put("bad_prepare", timedelta(seconds=789), prepare=bad_prepare)


def test_put_list():
    pd = ParamDict()
    pd.optional_list("a", None, ",")
    pd.optional_list("b", ["hello", "world"], ",")
    pd.optional_list("c", ["world", "hello"], ";")

    with pytest.raises(TypeError):
        pd.required_list("missing", None, ",")  # type: ignore

    assert pd.to_dict() == {
        "b": "hello,world",
        "c": "world;hello",
    }

    with pytest.raises(ValueError):
        pd.required_list("d", [], ",", nonempty=True)


def test_put_variants():
    pd = ParamDict()
    pd.optional_str("a", None)
    pd.optional_str("b", "hello")
    pd.optional_str("c", "world")
    assert pd.to_dict() == {
        "b": "hello",
        "c": "world",
    }

    pd = ParamDict()
    pd.optional_int("a", None)
    pd.optional_int("b", 123)
    pd.required_int("c", 456)
    assert pd.to_dict() == {
        "b": "123",
        "c": "456",
    }

    pd = ParamDict()
    pd.optional_float("a", None)
    pd.optional_float("b", 123.456)
    pd.required_float("c", 456.789)
    assert pd.to_dict() == {
        "b": "123.456",
        "c": "456.789",
    }

    pd = ParamDict()
    pd.optional_duration("a", None, TimeUnit.SECONDS)
    pd.optional_duration("b", timedelta(minutes=1), TimeUnit.SECONDS)
    pd.required_duration("c", timedelta(minutes=0.5), TimeUnit.SECONDS)
    assert pd.to_dict() == {
        "b": "60",
        "c": "30",
    }

    with pytest.raises(ValueError):
        pd.required_duration("d", math.inf, TimeUnit.SECONDS)

    pd = ParamDict()
    pd.optional_path("a", None)
    pd.optional_path("b", "hello/world")
    pd.required_path("c", "hello/world")
    pd.required_path("d", PureWindowsPath("hello", "world"))
    pd.required_path("e", PurePosixPath("hello", "world"))
    pd.required_path("g", r"hello\world")

    assert pd.to_dict() == dict.fromkeys(
        ("b", "c", "d", "e", "g"),
        "hello/world",
    )
