from io import BytesIO
from typing import Any, Dict, Mapping, Optional
from urllib.parse import parse_qsl

import pytest
from aiohttp import BodyPartReader, FormData, MultipartReader, hdrs

from aioqbt.api.torrents import AddFormBuilder

# Map bool to its string
_BOOL_STR: Mapping[Any, str] = {
    True: "true",
    False: "false",
}


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
