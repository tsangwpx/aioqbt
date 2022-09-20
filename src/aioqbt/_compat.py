import sys
from enum import Enum
from typing import Any, Callable, Optional, Type, TypeVar, overload

T = TypeVar("T")
E = TypeVar("E", bound=Enum)


@overload
def repr_enum(cls: None) -> Callable[[Type[E]], Type[E]]:
    pass


@overload
def repr_enum(cls: Type[E]) -> Type[E]:
    pass


def repr_enum(
    cls=None,
):
    """
    Preserve str() and format() behavior of enum types from underlying
    data type.

    Decorate an enum subclass mixed with a data type such that str() and
    format() return the equivalent result similar to the function
    directly operated on the objects of the data type.

    Mimic ReprEnum on Python 3.11.
    See https://github.com/python/cpython/issues/85955
    """

    def decorate(cls: Type[E]) -> Type[E]:
        if not issubclass(cls, Enum):
            raise TypeError(f"require subclass of Enum instead of {cls!r}")

        mro = tuple(cls.__mro__)

        # Find the first enum subclass in mro except cls itself
        enum_idx = next(i for i, s in enumerate(mro[1:], 1) if issubclass(s, Enum))
        enum_type = mro[enum_idx]
        mixin_types = mro[1:enum_idx]

        member_type = cls._member_type_  # type: ignore
        if member_type is object or member_type not in mixin_types:
            raise TypeError("repr_enum() only decorate enum types mixed with a data type")

        # If both cls and enum_type refer to the same method,
        # assume that the method is set by EnumMeta
        # even though the method may be explicitly defined in mixins

        if cls.__format__ is enum_type.__format__:
            cls.__format__ = member_type.__format__  # type: ignore

        if cls.__str__ is enum_type.__str__:
            # object.__str__ delegate to member_type.__repr__
            if member_type.__str__ is object.__str__:
                str_method = member_type.__repr__
            else:
                str_method = member_type.__str__

            cls.__str__ = str_method  # type: ignore

        return cls

    if cls is None:
        return decorate  # pragma: no cover
    else:
        return decorate(cls)


if sys.version_info >= (3, 11):  # pragma: no cover
    from enum import IntEnum, StrEnum

    # avoid unused references
    assert True, (StrEnum, IntEnum)
else:

    @repr_enum
    class StrEnum(str, Enum):
        pass

    @repr_enum
    class IntEnum(int, Enum):
        pass


if sys.version_info >= (3, 8):
    from functools import cached_property

    assert True, cached_property
else:  # pragma: no cover

    class cached_property:
        """
        Modified from the functools.cached_property implementation on Python 3.8
        """

        def __init__(self, func):
            self.func: Callable[..., Any] = func
            self.name: Optional[str] = None
            self.__doc__ = func.__doc__

        def __set_name__(self, owner, name):
            if self.name is None:
                self.name = name
            elif self.name != name:
                raise TypeError(
                    f"cached_property cannot be associated with two different names"
                    f" ({self.name!r} and {name!r})"
                )

        def __get__(self, instance, owner=None):
            if instance is None:
                return self

            if self.name is None:
                raise TypeError("cached_property must be associated with a name")

            try:
                cache = instance.__dict__
            except AttributeError:
                raise TypeError(
                    "cached_property require __dict__ attribute to cache value"
                ) from None

            try:
                value = cache[self.name]
            except KeyError:
                value = self.func(instance)
                cache[self.name] = value
            return value
