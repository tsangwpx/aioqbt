from dataclasses import MISSING, dataclass
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)
from weakref import WeakKeyDictionary

from typing_extensions import Protocol

from aioqbt.exc import MapperError

__all__ = (
    "ConvertFn",
    "ObjectMapper",
    "inspect_raw_data",
)

T = TypeVar("T")
E = TypeVar("E", bound=Enum)
K = TypeVar("K")

_META_CONV = "convert"
_META_DEFAULT = "default"
_META_DEFAULT_FACTORY = "default_factory"

ATTR_RAW_DATA = "_aioqbt_raw_data"


class ConvertFn(Protocol):
    """
    Convert a simple value to complex one.
    """

    def __call__(self, value: Any, context: Mapping[Any, Any]) -> Any:
        pass


@dataclass
class _FieldInfo:
    convert: Optional[ConvertFn]
    default: Any
    default_factory: Optional[Callable[[], Any]]


@dataclass
class _TypeInfo(Generic[T]):
    fields: Mapping[str, _FieldInfo]
    slot_names: Sequence[str]
    default_fields: Sequence[str]


# Cache: type -> MappedTypeInfo
_REGISTRY: MutableMapping[Type[Any], _TypeInfo[Any]] = WeakKeyDictionary()


def _resolve_slot_names(cls: Type[T]) -> List[str]:
    # search public slot names (not prefixed with underscore)
    # modified from copyreg._slotnames()

    assert isinstance(cls, type)

    slot_names = []

    base: type
    slots: Union[str, Sequence[str]]
    for base in cls.__mro__:
        slots = getattr(base, "__slots__", ())

        if isinstance(slots, str):
            slots = (slots,)

        for name in slots:
            if name.startswith("_"):
                continue

            slot_names.append(name)

    return slot_names


def _resolve_type_info(cls: Type[T]) -> _TypeInfo[T]:
    """
    Gather dataclass information used by ObjectMapper
    """
    if not is_dataclass(cls):
        raise ValueError(f"{cls} must be a dataclass")

    slot_names = _resolve_slot_names(cls)
    fields: Dict[str, _FieldInfo] = {}
    default_fields: List[str] = []

    for field in dataclass_fields(cls):
        f_name = field.name
        f_metadata = field.metadata

        if f_name.startswith("_"):
            continue

        conv: Optional[ConvertFn] = f_metadata.get(_META_CONV)
        if conv is not None and not callable(conv):
            raise ValueError(f"'convert' functon for field {f_name!r} must be a callable")

        default = f_metadata.get(_META_DEFAULT, MISSING)
        default_factory = f_metadata.get(_META_DEFAULT_FACTORY, None)

        default_factory = None if default_factory is MISSING else default_factory

        if default_factory is not None and not callable(default_factory):
            raise ValueError(
                f"{f_name!r} expect a callable as default_factory instead of {default_factory!r}"
            )

        if default is not MISSING and default_factory is not None:
            raise ValueError(f"{f_name!r} cannot be given both default and default_factory")
        elif default is not MISSING or default_factory is not None:
            default_fields.append(f_name)

        fields[f_name] = _FieldInfo(
            convert=conv,
            default=default,
            default_factory=default_factory,
        )

    return _TypeInfo(
        fields=fields,
        slot_names=slot_names,
        default_fields=default_fields,
    )


class ObjectMapper:
    """
    Map JSON-result to Python objects.
    """

    def _find_type_info(self, rtype: Type[T]) -> _TypeInfo[T]:
        try:
            type_info = _REGISTRY[rtype]
        except KeyError:
            type_info = _resolve_type_info(rtype)
            _REGISTRY[rtype] = type_info

        return type_info

    def create_object(
        self,
        rtype: Type[T],
        data: Mapping[str, Any],
        context: Mapping[Any, Any],
    ) -> T:
        """
        Create an object from its data.
        """
        info = self._find_type_info(rtype)

        dict_data = dict(data)  # copy

        # Iterate over the dict to validate key name and to convert applicable fields
        for key, value in dict_data.items():
            field_info = info.fields.get(key)

            if field_info is None:
                if key.isidentifier() and not key.startswith("_"):
                    continue
                raise MapperError(f"Bad field name: {key!r}")

            if field_info.convert is not None:
                try:
                    dict_data[key] = field_info.convert(value, context)
                except Exception as ex:
                    raise MapperError(f"Cannot convert: {key!r}={value!r}") from ex

        # Fill fields with default values
        for key in info.default_fields:
            if key in dict_data:
                continue

            field_info = info.fields[key]
            if field_info.default is not MISSING:
                dict_data[key] = field_info.default
            elif field_info.default_factory is not None:
                dict_data[key] = field_info.default_factory()
            else:
                raise AssertionError("unreachable")

        # Separate slot fields and dict fields
        slot_data = []
        for key in info.slot_names:
            if key in dict_data:
                slot_data.append((key, dict_data.pop(key)))

        # Instantiate the object
        inst = rtype.__new__(rtype)
        if dict_data:
            vars(inst).update(dict_data)

        for key, value in slot_data:
            setattr(inst, key, value)

        setattr(inst, ATTR_RAW_DATA, data)

        return inst

    def create_list(
        self,
        rtype: Type[T],
        data: Sequence[Mapping[str, Any]],
        context: Mapping[Any, Any],
    ) -> List[T]:
        """
        Create a list of objects from a list of data.
        """
        result = []

        for i, item in enumerate(data):
            result.append(self.create_object(rtype, item, context))

        return result

    def create_dict(
        self,
        rtype: Type[T],
        data: Mapping[K, Mapping[str, Any]],
        context: Mapping[Any, Any],
    ) -> Dict[K, T]:
        """
        Create a dict whose values are mapped from another dict.
        """
        result = {}

        for key, value in data.items():
            result[key] = self.create_object(rtype, value, context)

        return result


def inspect_raw_data(instance) -> Dict[str, Any]:
    """Return the raw dict from which the instance is created"""
    try:
        return getattr(instance, ATTR_RAW_DATA)
    except AttributeError:
        raise LookupError from None
