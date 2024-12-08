"""
Tools that create objects representing API results.

This module is internal to the package.
End users should not import this module directly.
"""

import builtins
import dataclasses
import sys
from dataclasses import MISSING, dataclass, is_dataclass
from enum import Enum
from typing import (
    TYPE_CHECKING,
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
    overload,
)

from typing_extensions import Protocol, dataclass_transform

from aioqbt.exc import MapperError

__all__ = (
    "ConvertFn",
    "ObjectMapper",
    "inspect_raw_data",
    "declarative",
    "field",
)

T = TypeVar("T")
E = TypeVar("E", bound=Enum)
K = TypeVar("K")

if TYPE_CHECKING:
    # mypy go here due to TYPE_CHECKING
    # avoid that 'type' object is not subscriptable in py37 and py38
    _FieldSequence = Sequence[dataclasses.Field[Any]]
else:
    _FieldSequence = Sequence[dataclasses.Field]

_META_CONV = "convert"

ATTR_RAW_DATA = "_aioqbt_raw_data"
ATTR_TYPE_INFO = "_aioqbt_type_info"


class _MissingRepr:
    def __repr__(self) -> str:
        """return ``MISSING`` when format/print"""
        return "MISSING"


MISSING_REPR = _MissingRepr()


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


def _find_type_info(rtype: Type[T]) -> _TypeInfo[T]:
    try:
        return getattr(rtype, ATTR_TYPE_INFO)  # type: ignore[no-any-return]
    except AttributeError:
        pass

    info = _resolve_type_info(rtype)
    setattr(rtype, ATTR_TYPE_INFO, info)

    import warnings

    warnings.warn(DeprecationWarning("Use @declarative() instead"))

    return info


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

    for field in dataclasses.fields(cls):
        f_name = field.name
        f_metadata = field.metadata

        if f_name.startswith("_"):
            continue

        conv: Optional[ConvertFn] = f_metadata.get(_META_CONV)
        if conv is not None and not callable(conv):
            raise ValueError(f"'convert' functon for field {f_name!r} must be a callable")

        default = field.default
        default_factory = None if field.default_factory is MISSING else field.default_factory

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

    def create_object(
        self,
        rtype: Type[T],
        data: Mapping[str, Any],
        context: Mapping[Any, Any],
    ) -> T:
        """
        Create an object from its data.
        """
        info = _find_type_info(rtype)

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


def inspect_raw_data(instance: Any) -> Dict[str, Any]:
    """Return the raw dict from which the instance is created"""
    try:
        return getattr(instance, ATTR_RAW_DATA)  # type: ignore[no-any-return]
    except AttributeError:
        raise LookupError from None


@overload
def field(
    *,
    default: T,
    init: bool = ...,
    repr: bool = ...,
    compare: bool = ...,
    hash: Optional[bool] = ...,
    convert: Optional[ConvertFn] = ...,
    metadata: Optional[Mapping[Any, Any]] = ...,
) -> T: ...


@overload
def field(
    *,
    default_factory: Callable[[], T],
    init: bool = ...,
    repr: bool = ...,
    compare: bool = ...,
    hash: Optional[bool] = ...,
    convert: Optional[ConvertFn] = ...,
    metadata: Optional[Mapping[Any, Any]] = ...,
) -> T: ...


@overload
def field(
    *,
    init: bool = ...,
    repr: bool = ...,
    compare: bool = ...,
    hash: Optional[bool] = ...,
    convert: Optional[ConvertFn] = ...,
    metadata: Optional[Mapping[Any, Any]] = ...,
) -> Any: ...


def field(
    *,
    default: Any = MISSING,
    default_factory: Any = MISSING,
    init: bool = True,
    repr: bool = True,
    compare: bool = True,
    hash: Optional[bool] = None,
    convert: Optional[ConvertFn] = None,
    metadata: Optional[Mapping[Any, Any]] = None,
) -> Any:
    """
    Field specifier of :func:`@declarative <.declarative>`.

    This is implemented as a wrapper of :func:`dataclasses.field` and, thus, a replacement.
    """

    # Since MISSING type is private, typing.Any is used in default and default_factory.
    # Return Any/T instead of Field[T] such that annotation matches in class definition.

    if metadata is None:
        metadata = {}
    else:
        metadata = dict(metadata)

    if convert is not None:
        if "convert" in metadata:
            raise ValueError("Cannot specify 'convert' in both argument and metadata")
        metadata["convert"] = convert

    if not metadata:
        metadata = None

    if default_factory is MISSING:
        return dataclasses.field(
            default=default,
            init=init,
            repr=repr,
            compare=compare,
            hash=hash,
            metadata=metadata,
        )
    elif default is MISSING:
        return dataclasses.field(
            default_factory=default_factory,
            init=init,
            repr=repr,
            compare=compare,
            hash=hash,
            metadata=metadata,
        )
    else:
        raise ValueError("Cannot specify both default and default_factory")


@overload
def declarative(cls: Type[T]) -> Type[T]: ...


@overload
def declarative(
    *,
    init: bool = True,
    repr: bool = True,
    eq: bool = True,
    unsafe_hash: bool = False,
    frozen: bool = False,
) -> Callable[[Type[T]], Type[T]]: ...


# PEP 681 - Data Class Transforms
# https://peps.python.org/pep-0681/
@dataclass_transform(
    field_specifiers=(
        dataclasses.Field,
        dataclasses.field,
        field,
    ),
)
def declarative(
    cls: Optional[Type[T]] = None,
    *,
    init: bool = True,
    repr: bool = True,
    eq: bool = True,
    unsafe_hash: bool = False,
    frozen: bool = False,
) -> Union[Type[T], Callable[[Type[T]], Type[T]]]:
    """
    Decorate a class to behave similarly to dataclass
    """

    def decorate(cls: Type[T]) -> Type[T]:
        cls = _process_class(
            cls,
            init=init,
            repr=repr,
            eq=eq,
            unsafe_hash=unsafe_hash,
            frozen=frozen,
        )

        type_info = _resolve_type_info(cls)
        setattr(cls, ATTR_TYPE_INFO, type_info)

        return cls

    if cls is None:
        return decorate

    return decorate(cls)


def _process_class(
    cls: Type[T],
    *,
    init: bool,
    repr: bool,
    eq: bool,
    unsafe_hash: bool,
    frozen: bool,
) -> Type[T]:
    """
    Fix AttributeError in __eq__, __hash__, __repr__ due to missing attributes.
    """

    # Note that @declarative() leverages dataclasses facilities.
    # However, ObjectMapper instantiates objects without invoking __init__().
    # If __eq__, __hash__, and __repr__ are added by dataclasses,
    # they are replaced with our ones to avoid AttributeError.

    old_methods = {s: getattr(cls, s, None) for s in ("__eq__", "__hash__", "__repr__")}

    wrap = dataclasses.dataclass(
        init=init,
        repr=repr,
        eq=eq,
        unsafe_hash=unsafe_hash,
        frozen=frozen,
    )
    cls = wrap(cls)

    def is_changed(name: str) -> bool:
        old = old_methods[name]
        new = getattr(cls, name, None)
        return new is not None and old is not new

    fields = dataclasses.fields(cls)  # type: ignore[arg-type]
    module = sys.modules.get(cls.__module__)
    globals = {} if module is None else vars(module)

    if is_changed("__eq__"):
        setattr(cls, "__eq__", _eq_fn(fields, globals=globals))

    if is_changed("__hash__"):
        setattr(cls, "__hash__", _hash_fn(fields, globals=globals))

    if is_changed("__repr__"):
        setattr(cls, "__repr__", _repr_fn(fields, globals=globals))

    return cls


def _eq_fn(
    fields: _FieldSequence,
    *,
    globals: Optional[Dict[str, object]] = None,
) -> Callable[..., str]:
    locals: Dict[str, object] = {
        "MISSING": dataclasses.MISSING,
    }
    args = ("self", "other")
    attrs = [f.name for f in fields if f.compare]
    self_tuple = _getattr_tuple_str("self", attrs, "MISSING")
    other_tuple = _getattr_tuple_str("other", attrs, "MISSING")
    body = [
        "if type(self) is type(other):",
        f" return {self_tuple} == {other_tuple}",
        "return NotImplemented",
    ]

    return _create_fn("__eq__", args, body, locals=locals, globals=globals)


def _hash_fn(
    fields: _FieldSequence,
    *,
    globals: Optional[Dict[str, object]] = None,
) -> Callable[..., int]:
    locals: Dict[str, object] = {
        "MISSING": dataclasses.MISSING,
    }
    args = ("self",)
    attrs = [f.name for f in fields if (f.compare if f.hash is None else f.hash)]
    self_tuple = _getattr_tuple_str("self", attrs, "MISSING")
    body = [f"return hash({self_tuple})"]

    return _create_fn("__hash__", args, body, locals=locals, globals=globals)


def _repr_fn(
    fields: _FieldSequence,
    *,
    globals: Optional[Dict[str, object]] = None,
) -> Callable[..., str]:
    locals: Dict[str, object] = {
        "MISSING_REPR": MISSING_REPR,
    }
    args = ("self",)
    txt = "".join(
        [f" {f.name}={{getattr(self, {f.name!r}, MISSING_REPR)!r}}" for f in fields if f.repr]
    )
    body = [
        f'return f"<{{type(self).__name__}}{txt}>"',
    ]
    fn = _create_fn("__repr__", args, body, locals=locals, globals=globals)
    from reprlib import recursive_repr

    wrap = recursive_repr()
    return wrap(fn)


# modified from dataclasses.py
def _getattr_tuple_str(
    name: str,
    attrs: Sequence[str],
    default: str,
) -> str:
    if not attrs:
        return "()"

    return f"({','.join([f'getattr({name}, {s!r}, {default})' for s in attrs])},)"


def _create_fn(
    name: str,
    args: Sequence[str],
    body: Sequence[str],
    *,
    globals: Optional[Dict[str, object]] = None,
    locals: Optional[MutableMapping[str, object]] = None,
    return_type: Any = dataclasses.MISSING,
) -> Callable[..., Any]:
    if locals is None:
        locals = {}
    if "BUILTINS" not in locals:
        locals["BUILTINS"] = builtins
    return_annotation = ""
    if return_type is not dataclasses.MISSING:
        locals["_return_type"] = return_type
        return_annotation = "->_return_type"

    args_txt = ", ".join(args)
    body_txt = "\n".join([f"  {s}" for s in body])

    # Compute the text of the entire function.
    txt = f" def {name}({args_txt}){return_annotation}:\n{body_txt}"

    local_vars = ", ".join(locals.keys())
    source = f"def _create_fn({local_vars}):\n{txt}\n return {name}"

    ns: Dict[str, Any] = {}
    exec(source, globals, ns)
    fn: Callable[..., T] = ns["_create_fn"](**locals)
    return fn
