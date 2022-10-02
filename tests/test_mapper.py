from dataclasses import dataclass, field
from typing import Any

import pytest

from aioqbt.exc import MapperError
from aioqbt.mapper import ATTR_RAW_DATA, ObjectMapper, inspect_raw_data


@dataclass
class Simple:
    integer: int
    string: str
    payload: Any

    _private: str = "class variable"


def test_mapper_object():
    data = {
        "integer": 12345,
        "string": "hello",
        "extra": "world",
    }

    mapper = ObjectMapper()
    inst = mapper.create_object(Simple, data, {})

    assert inst.integer == 12345
    assert inst.string == "hello"
    assert inspect_raw_data(inst) == data

    assert inst.extra == "world"  # type: ignore[attr-defined]

    assert inst._private == "class variable"
    inst._private = "inst variable"
    assert inst._private == "inst variable"


def test_mapper_list():
    data = [
        {
            "integer": s,
            "string": "hello",
        }
        for s in range(5)
    ]
    mapper = ObjectMapper()
    result_list = mapper.create_list(Simple, data, {})
    assert isinstance(result_list, list)
    assert len(result_list) == len(data)
    assert all(isinstance(s, Simple) for s in result_list)
    assert all(inspect_raw_data(a) == b for a, b in zip(result_list, data))
    assert all(a.integer == b["integer"] for a, b in zip(result_list, data))


def test_mapper_dict():
    marker = object()
    data = {
        "key": {
            "integer": 12345,
            "string": "hello",
            "payload": "key",
        },
        marker: {
            "integer": 12345,
            "string": "hello",
            "payload": marker,
        },
    }

    mapper = ObjectMapper()
    result_dict = mapper.create_dict(Simple, data, {})
    assert isinstance(result_dict, dict)
    assert result_dict.keys() == data.keys()
    for key in data.keys():
        assert isinstance(result_dict[key], Simple)
        assert inspect_raw_data(result_dict[key]) == data[key]
        assert result_dict[key].payload == key


def test_bad_class():
    mapper = ObjectMapper()

    class NotDataclass:
        pass

    with pytest.raises(ValueError):
        mapper.create_object(NotDataclass, {}, {})


def test_bad_data():
    mapper = ObjectMapper()
    with pytest.raises(MapperError):
        data = {"_private": "not allowed"}
        mapper.create_object(Simple, data, {})

    with pytest.raises(LookupError):
        inspect_raw_data(object())


def test_convert_error():
    @dataclass
    class Item:
        value: int = field(
            metadata={
                "convert": int,
            }
        )

    mapper = ObjectMapper()
    with pytest.raises(MapperError):
        mapper.create_object(Item, {"value": "not_integer"}, {})


@dataclass
class Base:
    __slots__ = ATTR_RAW_DATA


@dataclass
class User(Base):
    __slots__ = ("uid", "name", "__dict__")

    uid: int
    name: str
    topic: Any


def test_slots():
    mapper = ObjectMapper()

    inst = mapper.create_object(Base, {}, {})
    assert isinstance(inst, Base)
    assert inspect_raw_data(inst) == {}

    data = {
        "uid": 111,
        "name": "testing",
        "topic": "python",
    }

    inst = mapper.create_object(User, data, {})
    assert isinstance(inst, User)
    assert inspect_raw_data(inst) == data
    assert inst.uid == 111
    assert inst.name == "testing"
    assert inst.topic == "python"


def test_bad_fields():
    mapper = ObjectMapper()

    @dataclass
    class NotCallableConvert:
        value: int = field(
            metadata={
                "convert": object(),
            }
        )

    with pytest.raises(ValueError, match="convert"):
        mapper.create_object(NotCallableConvert, {}, {})

    @dataclass
    class NotCallableFactory:
        value: int = field(
            metadata={
                "default_factory": object(),
            }
        )

    with pytest.raises(ValueError, match="default_factory"):
        mapper.create_object(NotCallableFactory, {}, {})

    @dataclass
    class BothDefaultAndFactory:
        value: int = field(
            metadata={
                "default": 1,
                "default_factory": lambda: 2,
            }
        )

    with pytest.raises(ValueError, match="both"):
        mapper.create_object(BothDefaultAndFactory, {}, {})


def test_convert():
    @dataclass
    class Item:
        value: int = field(
            metadata={
                "convert": lambda val, ctx: val + 100,
            }
        )
        value2: int = field(
            metadata={
                "default": 2,
                "convert": lambda val, ctx: val + 200,
            }
        )
        value3: int = field(
            metadata={
                "default_factory": lambda: 3,
                "convert": lambda val, ctx: val + 300,
            }
        )

    data = {
        "value": 1,
        "value2": 2,
        "value3": 3,
    }

    mapper = ObjectMapper()
    inst = mapper.create_object(Item, data, {})
    assert inst.value == 101
    assert inst.value2 == 202
    assert inst.value3 == 303

    data = {
        "value": 10,
    }
    inst = mapper.create_object(Item, data, {})
    assert inst.value == 110
    assert inst.value2 == 2
    assert inst.value3 == 3
