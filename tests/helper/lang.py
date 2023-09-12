import asyncio
import functools
import logging
import random
import sys
import time
from typing import Awaitable, Callable, Optional, Tuple, Type, Union


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


if sys.version_info >= (3, 9):

    def randbytes(r: random.Random, n: int) -> bytes:
        return r.randbytes(n)

else:

    def randbytes(r: random.Random, n: int) -> bytes:
        return r.getrandbits(n * 8).to_bytes(n, "little")


def retry_assert(
    fn=None,
    *,
    max_attempts: int = 4,
    pause: Optional[float] = None,
    delay: Optional[float] = None,
    exc_types: Union[Type[BaseException], Tuple[Type[BaseException], ...], None] = None,
    logger: Optional[logging.Logger] = None,
):
    """
    Retry a coroutine if AssertionError raise.

    :param fn: function being decorated
    :param int max_attempts: maximum number of attempts
    :param float|None delay: initial delay
    :param float|None pause: pause between attempts
    :param exc_types: exception types to catch. The default value is `AssertionError`
    :param logger: logger to record failed attempt
    """

    if max_attempts <= 0:
        raise ValueError("max_attempts <= 0")

    if fn is None:
        return functools.partial(
            retry_assert,
            pause=pause,
            delay=delay,
            max_attempts=max_attempts,
            exc_types=exc_types,
            logger=logger,
        )

    if pause is None:
        pause = 1

    if delay is None:
        delay = 0

    if exc_types is None:
        exc_types = AssertionError

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        assert pause is not None
        assert delay is not None

        await asyncio.sleep(delay)

        last_exception: Optional[BaseException] = None

        for count in range(1, max_attempts + 1):
            try:
                return await fn(*args, **kwargs)
            except exc_types as ex:
                last_exception = ex

                if logger is not None:
                    logger.warning("Attempt %d/%d failed", count, max_attempts, exc_info=True)

            if count < max_attempts:
                await asyncio.sleep(pause)

        assert last_exception is not None

        raise last_exception

    return wrapper
