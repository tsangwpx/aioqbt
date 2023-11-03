from datetime import timedelta
from io import BytesIO
from typing import Any, Dict, Mapping, Optional, Union
from urllib.parse import parse_qsl

import pytest
from aiohttp import BodyPartReader, FormData, MultipartReader, hdrs

from aioqbt.api.torrents import AddFormBuilder
from aioqbt.api.types import InactiveSeedingTimeLimits
from aioqbt.chrono import Minutes

# Map bool to its string
_BOOL_STR: Mapping[Any, str] = {
    True: "true",
    False: "false",
}

_DUMMY_HASH = "0" * 40


class StreamWriter:
    def __init__(self, buffer: bytearray) -> None:
        self._buf = buffer

    async def write(self, buf: bytes) -> None:
        self._buf.extend(buf)


class StreamReader:
    def __init__(self, buf: bytes) -> None:
        self._bio = BytesIO(buf)

    async def read(self, n: int = -1) -> bytes:
        return self._bio.read(n)

    async def readline(self, n: int = -1) -> bytes:
        return self._bio.readline(n)


async def consume_form(form: FormData) -> Dict[str, Any]:
    """
    Consume FormData and return its contents as dict
    """
    # reference: aiohttp.web_request:BaseRequest.post
    result: Dict[str, Any] = {}
    buffer = bytearray()
    writer: Any = StreamWriter(buffer)
    multipart = form()
    await multipart.write(writer)

    if multipart.content_type.startswith("multipart/"):
        stream_headers = {
            str(hdrs.CONTENT_TYPE): multipart.content_type,
        }
        stream: Any = StreamReader(buffer)
        reader = MultipartReader(stream_headers, stream)

        while True:
            part = await reader.next()

            if part is None:
                break

            if isinstance(part, BodyPartReader):
                if part.name is None:
                    raise ValueError("Missing part name?")

                data = await part.read(decode=True)

                part_ct = part.headers.get(hdrs.CONTENT_TYPE)

                if part.filename:
                    result[part.name] = (part.filename, data, part.headers)
                elif part_ct is None or part_ct.startswith("text/"):
                    charset = part.get_charset(default="utf-8")
                    result[part.name] = data.decode(charset)
                else:
                    result[part.name] = data

                await part.release()
            else:
                raise ValueError(f"Nested multipart? {type(part)}")
    else:
        charset = "utf-8"
        qsl = parse_qsl(
            buffer.decode(charset),
            keep_blank_values=True,
            encoding=charset,
        )
        result.update(qsl)

    return result


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [True, False, None])
async def test_top_queue(value: Optional[bool]) -> None:
    form = AddFormBuilder().add_to_top_of_queue(value).build()
    data = await consume_form(form)
    assert data.get("addToTopOfQueue") == _BOOL_STR.get(value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        (Minutes(1234), "1234"),
        (timedelta(hours=1), "60"),
        (timedelta(minutes=1440), "1440"),
        (timedelta(seconds=30), "0"),
        (InactiveSeedingTimeLimits.GLOBAL, str(InactiveSeedingTimeLimits.GLOBAL)),
        (InactiveSeedingTimeLimits.UNLIMITED, str(InactiveSeedingTimeLimits.UNLIMITED)),
    ],
)
async def test_inactive_seeding_time_limit(
    value: Union[timedelta, Minutes, None],
    expected: Optional[str],
) -> None:
    form = AddFormBuilder().inactive_seeding_time_limit(value).include_url(_DUMMY_HASH).build()
    data = await consume_form(form)
    assert data.get("inactiveSeedingTimeLimit") == expected
