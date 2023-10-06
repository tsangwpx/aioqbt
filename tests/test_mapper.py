from typing import Any

import pytest

from aioqbt.exc import MapperError
from aioqbt.mapper import ATTR_RAW_DATA, ObjectMapper, declarative, field, inspect_raw_data


@pytest.fixture
def mapper():
    return ObjectMapper()


@declarative
class Simple:
    integer: int
    string: str
    payload: Any


def test_mapper_object(mapper: ObjectMapper):
    marker = object()
    data = {
        "integer": 123,
        "string": "abc",
        "payload": "payload",
    }
    obj = mapper.create_object(Simple, data, {})

    assert obj.integer == 123
    assert obj.string == "abc"
    assert obj.payload == "payload"
    assert obj == obj, "self equality"
    assert getattr(Simple, "__hash__") is None
    assert inspect_raw_data(obj) == data

    obj2 = mapper.create_object(Simple, data, {})
    assert obj == obj2

    # extra fields
    data_extra = {
        **data,
        "extra": marker,
    }
    obj_extra = mapper.create_object(Simple, data_extra, {})

    assert obj_extra.extra == marker  # type: ignore[attr-defined]
    assert obj_extra == obj_extra
    assert obj_extra == obj
    assert inspect_raw_data(obj_extra) == data_extra

    # missing fields
    data_missing = data.copy()
    del data_missing["string"]
    obj_missing = mapper.create_object(Simple, data_missing, {})

    with pytest.raises(AttributeError):
        _ = obj_missing.string

    assert obj_missing == obj_missing
    assert obj_missing != obj
    assert obj_missing != obj_extra
    assert inspect_raw_data(obj_missing) == data_missing

    obj_missing2 = mapper.create_object(Simple, data_missing, {})
    assert obj_missing == obj_missing2


def test_mapper_list(mapper: ObjectMapper):
    data = [
        {
            "integer": s,
            "string": "hello",
        }
        for s in range(5)
    ]
    result_list = mapper.create_list(Simple, data, {})
    assert isinstance(result_list, list)
    assert len(result_list) == len(data)
    assert all(isinstance(s, Simple) for s in result_list)
    assert all(inspect_raw_data(a) == b for a, b in zip(result_list, data))
    assert all(a.integer == b["integer"] for a, b in zip(result_list, data))


def test_mapper_dict(mapper: ObjectMapper):
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

    result_dict = mapper.create_dict(Simple, data, {})
    assert isinstance(result_dict, dict)
    assert result_dict.keys() == data.keys()
    for key in data.keys():
        assert isinstance(result_dict[key], Simple)
        assert inspect_raw_data(result_dict[key]) == data[key]
        assert result_dict[key].payload == key


def test_declarative_compare(mapper: ObjectMapper):
    @declarative
    class User:
        id: int
        name: str = field(compare=False)

    data = {
        "id": 0,
        "name": "root",
    }
    data2 = {
        "id": 0,
        "name": "admin",
    }
    user = mapper.create_object(User, data, {})
    user2 = mapper.create_object(User, data2, {})

    assert user == user
    assert user == user2


def test_declarative_hash(mapper: ObjectMapper):
    @declarative(unsafe_hash=True)
    class User:
        id: int
        name: str = field(hash=False)

    data = {
        "id": 0,
        "name": "root",
    }
    data2 = {
        "id": 0,
        "name": "admin",
    }
    data3 = {
        "id": 1,
        "name": "root",
    }
    user = mapper.create_object(User, data, {})
    user2 = mapper.create_object(User, data2, {})
    user3 = mapper.create_object(User, data3, {})

    assert user == user
    assert hash(user) == hash(user)

    assert user != user2
    assert hash(user) == hash(user2)

    assert user != user3
    assert hash(user) != hash(user3)


def test_declarative_repr(mapper: ObjectMapper):
    @declarative
    class Book:
        title: str
        author: str = field(repr=False)

    data = {
        "title": "Python101",
        "author": "nobody",
    }
    book = mapper.create_object(Book, data, {})

    assert "title=" in repr(book)
    assert "author=" not in repr(book)

    data2 = {
        "name": "nobody",
    }
    book2 = mapper.create_object(Book, data2, {})
    assert "title=MISSING" in repr(book2)


def test_bad_class(mapper: ObjectMapper):
    class NotDeclarative:
        pass

    with pytest.raises(ValueError):
        mapper.create_object(NotDeclarative, {}, {})


def test_bad_data(mapper: ObjectMapper):
    with pytest.raises(MapperError):
        data = {"_private": "not allowed"}
        mapper.create_object(Simple, data, {})

    with pytest.raises(LookupError):
        inspect_raw_data(object())


def test_convert_error(mapper: ObjectMapper):
    @declarative
    class Item:
        value: int = field(
            convert=lambda val, ctx: int(val),
        )

    with pytest.raises(MapperError):
        mapper.create_object(Item, {"value": "not_integer"}, {})


@declarative
class Base:
    __slots__ = ATTR_RAW_DATA


@declarative
class User(Base):
    __slots__ = ("uid", "name", "__dict__")

    uid: int
    name: str
    topic: Any


def test_slots(mapper: ObjectMapper):
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
    with pytest.raises(ValueError, match="convert"):

        @declarative
        class NotCallableConvert:
            value: int = field(
                convert=object(),  # type: ignore
            )

    with pytest.raises(ValueError, match="default_factory"):

        @declarative
        class NotCallableFactory:
            value: int = field(
                default_factory=object(),  # type: ignore[call-overload]
            )

    with pytest.raises(ValueError, match="both"):

        @declarative
        class BothDefaultAndFactory:
            value: int = field(  # type: ignore[call-overload]
                default=1,
                default_factory=lambda: 2,
            )


def test_convert(mapper: ObjectMapper):
    @declarative
    class Item:
        value: int = field(
            convert=lambda val, ctx: val + 100,
        )
        value2: int = field(
            default=2,
            convert=lambda val, ctx: val + 200,
        )
        value3: int = field(
            default=3,
            convert=lambda val, ctx: val + 300,
        )

    data = {
        "value": 1,
        "value2": 2,
        "value3": 3,
    }
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
