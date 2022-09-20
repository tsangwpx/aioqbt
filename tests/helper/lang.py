import asyncio
import random
import sys
import time
from typing import Any, Awaitable, Callable, Optional


async def one_moment(duration: float = 1 / 1000):
    """Pause for a moment"""
    await asyncio.sleep(duration)


async def busy_wait_for(
    predicate: Callable[[], Awaitable[bool]],
    timeout: float = 10,
    step: Optional[float] = None,
) -> bool:
    if step is None:
        step = max(timeout / 100, 0.01)

    now = time.monotonic()
    deadline = now + timeout

    while now < deadline:
        try:
            result = await asyncio.wait_for(predicate(), deadline - now)
        except asyncio.TimeoutError:
            break

        if result:
            return True

        await asyncio.sleep(step)
        now = time.monotonic()

    return False


async def busy_assert(
    evaluate: Callable[[], Awaitable[Any]],
    timeout: float = 10,
    step: Optional[float] = None,
):
    if step is None:
        step = max(timeout / 100, 0.01)

    now = time.monotonic()
    deadline = now + timeout

    has_result = False
    result = None

    while now < deadline:
        try:
            result = await asyncio.wait_for(evaluate(), deadline - now)
        except asyncio.TimeoutError:
            break

        if bool(result):
            return True

        has_result = True
        await asyncio.sleep(step)
        now = time.monotonic()

    if has_result:
        assert result
    else:
        assert False, "timeout"


async def busy_assert_eq(
    expected: Any,
    evaluate: Callable[[], Awaitable[Any]],
    extra: Any = None,
    timeout: float = 10,
    step: Optional[float] = None,
):
    if step is None:
        step = max(timeout / 100, 0.01)

    now = time.monotonic()
    deadline = now + timeout

    has_result = False
    result = None

    while now < deadline:
        try:
            result = await asyncio.wait_for(evaluate(), deadline - now)
        except asyncio.TimeoutError:
            break

        if expected == result:
            return True

        has_result = True
        await asyncio.sleep(step)
        now = time.monotonic()

    if has_result:
        assert expected == result, extra
    else:
        assert False, "timeout"


if sys.version_info >= (3, 9):

    def randbytes(r: random.Random, n: int) -> bytes:
        return r.randbytes(n)

else:

    def randbytes(r: random.Random, n: int) -> bytes:
        return r.getrandbits(n * 8).to_bytes(n, "little")
