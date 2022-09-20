import copy
from functools import wraps
from typing import Any, Callable, TypeVar, overload

Fn = TypeVar("Fn", bound=Callable[..., Any])


@overload
def copy_self(fn: None) -> Callable[[Fn], Fn]:
    pass


@overload
def copy_self(fn: Fn) -> Fn:
    pass


def copy_self(fn=None):
    """
    Copy the first argument before execute the wrapped function
    """
    if fn is None:
        return copy_self  # pragma: no cover

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        return fn(copy.copy(self), *args, **kwargs)

    return wrapper
