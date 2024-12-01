from datetime import timedelta
from io import BytesIO
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl

import pytest
from aiohttp import BodyPartReader, FormData, MultipartReader, hdrs
from helper.torrent import make_torrent_single

from aioqbt._compat import IntEnum, StrEnum
from aioqbt.api import AddFormBuilder


class EnumInt(IntEnum):
    MINUS_ONE = -1
    ZERO = 0
    ONE = 1


class EnumStr(StrEnum):
    EMPTY = ""
    HELLO = "hello"


class StreamWriter:
    def __init__(self, buffer: bytearray) -> None:
        self._buf = buffer

    async def write(self, buf: bytes) -> None:
        self._buf.extend(buf)


class StreamReader:
    def __init__(self, buf: bytes) -> None:
        self._buf = buf
        self._bio = BytesIO(buf)

    async def read(self, n: int = -1) -> bytes:
        return self._bio.read(n)

    async def readline(self, n: int = -1) -> bytes:
        return self._bio.readline(n)

    def unread_data(self, data: bytes) -> None:
        pos = self._bio.tell()
        start = pos - len(data)
        if start < 0:
            raise IOError("unread more than position")
        if self._buf[start:pos] != data:
            raise IOError("Data unmatched")
        self._bio.seek(start)

    def at_eof(self) -> bool:
        return self._bio.tell() == len(self._buf)


@pytest.fixture(
    scope="module",
    params=[
        "url",
        "file",
    ],
)
def builder(request: pytest.FixtureRequest) -> AddFormBuilder:
    """
    Builder may generate different form based on its payload
    """
    sample = make_torrent_single("dummy")
    param = request.param
    if param == "url":
        return AddFormBuilder().include_url(sample.magnet)
    elif param == "file":
        return AddFormBuilder().include_file(sample.data, f"{sample.name}.torrent")
    else:
        assert False, "unreachable"


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


def _friendly_param_id(values: List[Tuple[str, Callable[..., Any]]]) -> List[Any]:
    result = []
    for key, meth in values:
        result.append(pytest.param(key, meth, id=meth.__name__))
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,method",
    [
        ("useDownloadPath", AddFormBuilder.use_download_path),
        ("skip_checking", AddFormBuilder.skip_checking),
        ("paused", AddFormBuilder.paused),
        ("root_folder", AddFormBuilder.root_folder),
        ("autoTMM", AddFormBuilder.auto_tmm),
        ("sequentialDownload", AddFormBuilder.sequential_download),
        ("firstLastPiecePrio", AddFormBuilder.first_last_piece_prio),
        ("addToTopOfQueue", AddFormBuilder.add_to_top_of_queue),
    ],
)
@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(None, None, id="None"),
        pytest.param(True, "true", id="true"),
        pytest.param(False, "false", id="false"),
    ],
)
async def test_bool_methods(
    builder: AddFormBuilder,
    name: str,
    method: Callable[[AddFormBuilder, Any], AddFormBuilder],
    value: Optional[bool],
    expected: Optional[str],
):
    data = await consume_form(method(builder, value).build())
    assert data.get(name) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,method",
    [
        ("cookie", AddFormBuilder.cookie),
        ("category", AddFormBuilder.category),
        ("rename", AddFormBuilder.rename),
        ("stopCondition", AddFormBuilder.stop_condition),
        ("contentLayout", AddFormBuilder.content_layout),
        ("ssl_certificate", AddFormBuilder.ssl_certificate),
        ("ssl_private_key", AddFormBuilder.ssl_private_key),
        ("ssl_dh_params", AddFormBuilder.ssl_dh_params),
    ],
)
@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(None, None, id="None"),
        pytest.param("", "", id="empty"),
        pytest.param("plain text", "plain text", id="string"),
        pytest.param(EnumStr.HELLO, "hello", id="StrEnum"),
    ],
)
async def test_str_methods(
    builder: AddFormBuilder,
    name: str,
    method: Callable[[AddFormBuilder, Any], AddFormBuilder],
    value: Optional[str],
    expected: Optional[str],
):
    data = await consume_form(method(builder, value).build())
    assert data.get(name) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key,method",
    [
        ("dlLimit", AddFormBuilder.dl_limit),
        ("upLimit", AddFormBuilder.up_limit),
        ("shareLimitAction", AddFormBuilder.share_limit_action),
    ],
)
@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(None, None, id="None"),
        pytest.param(0, "0", id="0"),
        pytest.param(-1234, "-1234", id="minus_1234"),
        pytest.param(EnumInt.ONE, "1", id="enum_one"),
    ],
)
async def test_int_methods(
    builder: AddFormBuilder,
    key: str,
    method: Callable[[AddFormBuilder, Any], AddFormBuilder],
    value: Optional[int],
    expected: Optional[str],
):
    data = await consume_form(method(builder, value).build())
    assert data.get(key) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key,method",
    [
        ("ratioLimit", AddFormBuilder.ratio_limit),
    ],
)
@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(None, None, id="None"),
        pytest.param(0, "0.0", id="0"),
        pytest.param(-1234, "-1234.0", id="minus_1234"),
        pytest.param(EnumInt.MINUS_ONE, "-1.0", id="enum_minus_one"),
    ],
)
async def test_float_methods(
    builder: AddFormBuilder,
    key: str,
    method: Callable[[AddFormBuilder, Any], AddFormBuilder],
    value: Optional[int],
    expected: Optional[str],
):
    data = await consume_form(method(builder, value).build())
    assert data.get(key) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key,method",
    [
        ("savepath", AddFormBuilder.savepath),
        ("downloadPath", AddFormBuilder.download_path),
    ],
)
@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(None, None, id="None"),
        pytest.param(r"/hello/Downloads", r"/hello/Downloads", id="slash"),
        pytest.param(r"C:\Hello\Downloads", r"C:/Hello/Downloads", id="backslash"),
    ],
)
async def test_path_methods(
    builder: AddFormBuilder,
    key: str,
    method: Callable[[AddFormBuilder, Any], AddFormBuilder],
    value: Optional[str],
    expected: Optional[str],
):
    data = await consume_form(method(builder, value).build())
    assert data.get(key) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key,method",
    [
        ("seedingTimeLimit", AddFormBuilder.seeding_time_limit),
        ("inactiveSeedingTimeLimit", AddFormBuilder.inactive_seeding_time_limit),
    ],
)
@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(None, None, id="None"),
        pytest.param(0, "0", id="zero"),
        pytest.param(1234, "1234", id="int"),
        pytest.param(-1, "-1", id="negative"),
        pytest.param(timedelta(seconds=30), "0", id="timedelta_second"),
        pytest.param(timedelta(minutes=30), "30", id="timedelta_minute"),
        pytest.param(EnumInt.MINUS_ONE, "-1", id="enum_minus_one"),
    ],
)
async def test_time_limit_methods(
    builder: AddFormBuilder,
    key: str,
    method: Callable[[AddFormBuilder, Any], AddFormBuilder],
    value: Optional[int],
    expected: Optional[str],
):
    data = await consume_form(method(builder, value).build())
    assert data.get(key) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param([], "", id="0"),
        pytest.param(["hello"], "hello", id="1"),
        pytest.param(["hello", "world"], "hello,world", id="2"),
    ],
)
async def test_tags(builder: AddFormBuilder, value: Any, expected: Optional[str]):
    data = await consume_form(builder.tags(value).build())
    assert data.get("tags") == expected
