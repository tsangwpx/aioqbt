import copy
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, overload

T = TypeVar("T")
Fn = TypeVar("Fn", bound=Callable[..., Any])


@overload
def copy_self(fn: None) -> Callable[[Fn], Fn]:
    pass


@overload
def copy_self(fn: Fn) -> Fn:
    pass


def copy_self(fn: Optional[Callable[..., T]] = None) -> Any:
    """
    Copy the first argument before execute the wrapped function
    """
    if fn is None:
        return copy_self

    @wraps(fn)
    def wrapper(self: T, *args: Any, **kwargs: Any) -> T:
        return fn(copy.copy(self), *args, **kwargs)

    return wrapper
