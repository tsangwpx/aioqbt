import contextlib
import logging
import os
from dataclasses import dataclass, field
from http.cookies import Morsel
from typing import Any, AsyncIterator, Dict, List, Optional

import aiohttp

from aioqbt.client import APIClient, create_client
from aioqbt.version import APIVersion


@dataclass
class LoginInfo:
    url: str
    username: str
    password: str
    cookies: List[Any] = field(default_factory=list)


def parse_login(spec: str) -> LoginInfo:
    from urllib.parse import urlsplit

    parts = urlsplit(spec)

    username = parts.username
    password = parts.password

    if "@" in parts.netloc:
        _, _, hostname = parts.netloc.partition("@")
    else:
        hostname = parts.netloc

    url = f"{parts.scheme}://{hostname}{parts.path}"

    assert username is not None
    assert password is not None

    return LoginInfo(
        url=url,
        username=username,
        password=password,
    )


def parse_login_env(name: str) -> Optional[LoginInfo]:
    spec = os.environ.get(name)
    if spec is None:
        return None
    return parse_login(spec)


@contextlib.asynccontextmanager
async def _cleanup_context(client: APIClient) -> AsyncIterator[None]:
    """
    Make snapshots before and after yield.
    Remove hashes, categories, and tags newly found after yield.
    """

    async def torrent_hashes() -> Dict[str, str]:
        return {s["hash"]: s["name"] for s in await client.request_json("GET", "torrents/info")}

    async def category_names() -> List[str]:
        return list((await client.request_json("GET", "torrents/categories")).keys())

    async def tag_names() -> List[str]:
        if APIVersion.compare(client.api_version, (2, 3, 0)) < 0:
            return []

        return await client.request_json("GET", "torrents/tags")  # type: ignore[no-any-return]

    hashes = await torrent_hashes()
    categories = await category_names()
    tags = await tag_names()

    yield

    hashes2 = await torrent_hashes()
    categories2 = await category_names()
    tags2 = await tag_names()

    extra_hashes = {k: v for k, v in hashes2.items() if k not in hashes}
    extra_categories = set(categories2) - set(categories)
    extra_tags = set(tags2) - set(tags)

    if extra_hashes:
        logging.warning("Clean up torrents: %r", list(extra_hashes.values()))
        await client.request_text(
            "POST",
            "torrents/delete",
            data={
                "hashes": "|".join(extra_hashes.keys()),
                "deleteFiles": "true",
            },
        )

    if extra_categories:
        logging.info("Clean up categories: %r", list(extra_categories))
        await client.request_text(
            "POST",
            "torrents/removeCategories",
            data={
                "categories": "\n".join(extra_categories),
            },
        )

    if extra_tags:
        assert APIVersion.compare(client.api_version, (2, 3, 0)) >= 0
        logging.info("Clean up tags: %r", list(extra_tags))
        await client.request_text(
            "POST",
            "torrents/deleteTags",
            data={
                "tags": ",".join(extra_tags),
            },
        )


@contextlib.asynccontextmanager
async def client_context(login: LoginInfo, cookies: List[Any]) -> AsyncIterator[APIClient]:
    """
    Save/restore cookies if any. Otherwise, log in with credential.
    """

    http = aiohttp.ClientSession(
        cookies=login.cookies,
    )

    url = login.url
    username = login.username
    password = login.password

    client: Optional[APIClient] = None

    if login.cookies:
        client = await create_client(
            url=url,
            http=http,
            logout_when_close=False,
        )

        if client.api_version is None:
            # the cookies seem expired
            client = None

    if client is None:
        client = await create_client(
            url=url,
            username=username,
            password=password,
            logout_when_close=False,
            http=http,
        )

    new_cookies = []
    for item in list(http.cookie_jar):
        assert isinstance(item, Morsel)
        new_cookies.append((item.key, item))

    cookies[:] = new_cookies

    async with http:
        async with client:
            async with _cleanup_context(client):
                yield client
