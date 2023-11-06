import itertools
import logging
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, Dict, NamedTuple, Optional
from xml.etree.ElementTree import Element, SubElement
from xml.etree.ElementTree import tostring as stringify_xml

import pytest
import pytest_asyncio
from aiohttp import web
from helper.lang import retry_assert
from helper.web import temporary_web_server

from aioqbt.api.types import Preferences, RSSArticle, RSSFeed, RSSFolder, RSSRule
from aioqbt.client import APIClient
from aioqbt.version import APIVersion

# Note:
# tests usually create their RSS folders under root folder.
# This attempts to avoid interference from other tests.

NAME_TABLE = {
    "news": ["world", "local", "tech", "business", "health"],
    "elements": [
        f"{a} {b}"
        for a, b in itertools.product(
            ("gaseous", "liquid", "solid"),
            ("hydrogen", "carbon", "oxygen", "sodium"),
        )
    ],
}


def _build_rss_xml(
    title: str,
    count: int,
    base_url: str,
    *,
    season: Optional[int] = None,
    desc: str = "description",
) -> Element:
    """Build RSS in XML tree"""
    rss = Element("rss", {"version": "2.0"})
    channel = SubElement(rss, "channel")

    title_elem = SubElement(channel, "title")
    title_elem.text = title

    desc_elem = SubElement(channel, desc)
    desc_elem.text = desc

    names = NAME_TABLE.get(title)

    for idx in range(count):
        item_id = idx + 1

        item = SubElement(channel, "item")

        if season is None:
            episode = ""
        else:
            episode = f" s{season:02d}e{item_id:02d}"

        if names is None:
            item_name = f"item {item_id}"
        else:
            item_name = names[idx % len(names)]

        item_title = SubElement(item, "title")
        item_title.text = f"{title} - {item_name}{episode}"

        item_link = SubElement(item, "link")
        item_link.text = f"{base_url}/{title}-item-{item_id}"

        item_desc = SubElement(item, "description")
        item_desc.text = f"{title} item {item_id} desc"

    return rss


class FeedService(NamedTuple):
    url: str


@pytest_asyncio.fixture
async def feed_service():
    """
    Download RSS feed by HTTP

    The content is generated based on request path and query.
    """

    async def handler(request: web.BaseRequest):
        path = PurePosixPath(request.path)
        suffix = path.suffix

        try:
            if suffix == ".xml":
                title = str(request.query.get("title", path.stem))
                count = int(request.query.get("count", 1))
                try:
                    season = int(request.query.get("season"))  # type: ignore[arg-type]
                except (ValueError, TypeError):
                    season = None

                # utf-8 encoding result in bytes
                # xml_declaration was added in py38. do it manually later.
                body = stringify_xml(
                    _build_rss_xml(title, count, url, season=season),
                    encoding="utf-8",
                )
                assert isinstance(body, bytes)
                body = b"<?xml version='1.0' encoding='utf-8'?>" + body

                return web.Response(
                    body=body,
                    content_type="text/xml",
                )
        except web.HTTPException:
            # HTTP error response
            raise
        except BaseException:
            logging.error(
                "Exception when handling request %r",
                request,
                exc_info=True,
            )
            raise

        raise web.HTTPNotFound()

    async with temporary_web_server(handler) as url:
        yield FeedService(
            url=url,
        )


async def get_items(client: APIClient, with_data: bool) -> Dict[str, Any]:
    items = await client.request_json(
        "GET",
        "rss/items",
        params={
            "withData": "true" if with_data else "false",
        },
    )
    assert isinstance(items, dict)
    return items


@pytest.mark.asyncio
async def test_basic(client: APIClient, feed_service: FeedService):
    # test:
    # add_folder
    # add_feed
    # move_item
    # remove_item

    url = feed_service.url

    await client.rss.add_folder(r"news")
    await client.rss.add_folder(r"news\world")
    await client.rss.add_folder(r"news\asia")
    await client.rss.add_feed(f"{url}/alpha.xml", r"news\world\alpha")
    await client.rss.add_feed(f"{url}/beta.xml?count=2", r"news\world\beta")
    await client.rss.move_item(r"news\world\beta", r"news\asia\beta")

    def assert_feed(d: object, with_data: bool):
        """assert d is a dict of feed item"""
        assert isinstance(d, dict)
        assert d.keys() >= {"uid", "url"}
        assert isinstance(d["uid"], str)
        assert isinstance(d["url"], str)

        if not with_data:
            return

        assert d.keys() >= {"title", "lastBuildDate", "isLoading", "hasError", "articles"}
        assert isinstance(d["isLoading"], bool)
        assert isinstance(d["hasError"], bool)
        assert isinstance(d["articles"], list)

    async def assert_items(with_data: bool):
        items = await get_items(client, with_data)

        assert isinstance(items, dict)
        assert items.keys() >= {"news"}

        assert isinstance(items["news"], dict)
        assert items["news"].keys() == {"world", "asia"}
        assert items["news"]["world"].keys() == {"alpha"}
        assert items["news"]["asia"].keys() == {"beta"}

        assert_feed(items["news"]["world"]["alpha"], with_data)
        assert_feed(items["news"]["asia"]["beta"], with_data)

    await assert_items(False)
    await assert_items(True)

    await client.rss.remove_item(r"news")
    items = await get_items(client, False)
    assert "news" not in items


@pytest.mark.asyncio
async def test_items(client: APIClient, feed_service: FeedService, temp_prefs):
    # enable rss_processing_enabled to refresh RSS feeds in old qBittorrent versions
    prefs = Preferences()
    prefs["rss_processing_enabled"] = True
    await client.app.set_preferences(prefs)

    name = "items"
    url = feed_service.url

    await client.rss.add_folder(name)
    await client.rss.add_feed(f"{url}/items/news.xml", rf"{name}\news")

    @retry_assert
    async def assert_items(with_data: bool):
        root = await client.rss.items(with_data)

        assert isinstance(root, RSSFolder)

        assert "items" in root
        items = root["items"]
        assert isinstance(items, RSSFolder)

        # RSSFolder is a mapping
        assert len(items) == 1
        assert list(items) == ["news"]

        with pytest.raises(KeyError):
            _ = root["badkey"]

        with pytest.raises(KeyError):
            _ = root[r"\items"]  # empty part

        with pytest.raises(KeyError):
            _ = root[r"items\badkey"]

        assert "news" in items
        assert root[r"items\news"] == items[r"news"]

        feed = items["news"]
        assert isinstance(feed, RSSFeed)

        assert isinstance(feed.url, str)
        assert isinstance(feed.uid, str)

        if with_data:
            assert isinstance(feed.title, str)
            assert isinstance(feed.lastBuildDate, str)
            assert isinstance(feed.isLoading, bool)
            assert isinstance(feed.hasError, bool)
            assert isinstance(feed.articles, list)
            assert len(feed.articles)
            assert set(type(s) for s in feed.articles) == {RSSArticle}

            # check one of articles.
            article = feed.articles[0]

            assert isinstance(article.id, str)
            assert isinstance(article.title, str)
            assert isinstance(article.description, str)
            assert isinstance(article.date, datetime)
            assert isinstance(article.link, str)
            assert isinstance(article.torrentURL, str)

    await assert_items(False)
    await assert_items(True)

    await client.rss.remove_item(name)


@pytest.mark.asyncio
async def test_refresh_items(client: APIClient, feed_service: FeedService):
    if APIVersion.compare(client.api_version, (2, 2, 1)) < 0:
        pytest.skip("API 2.2.1")

    name = "refresh"
    url = feed_service.url

    await client.rss.add_feed(f"{url}/refresh.xml?count=2", name)

    async def assert_newly_added():
        items = await get_items(client, True)
        feed = items[name]
        assert isinstance(feed, dict)
        assert len(feed["articles"]) == 0

    await assert_newly_added()

    await client.rss.refresh_item(name)

    @retry_assert
    async def assert_refresh():
        items = await get_items(client, True)
        feed = items[name]
        assert isinstance(feed, dict)
        assert len(feed["articles"]) == 2

    await assert_refresh()

    await client.rss.remove_item(name)


@pytest.mark.asyncio
async def test_rules(client: APIClient, temp_prefs):
    rule1 = RSSRule(
        enabled=False,
        mustContain="mustContain",
        mustNotContain="mustNotContain",
        episodeFilter="1x1-13;",
    )
    rule2 = RSSRule(mustContain="rule2")
    rule3 = RSSRule(
        mustContain="rule3",
    )

    await client.rss.set_rule("rule1", rule1)
    await client.rss.set_rule("rule2", rule2)
    await client.rss.set_rule("rule3", rule3)
    await client.rss.remove_rule("rule2")
    await client.rss.rename_rule("rule3", "rule3new")

    def assert_rule(rule: RSSRule):
        assert isinstance(rule, dict)
        assert rule.keys() >= {"enabled", "mustContain", "mustNotContain", "useRegex"}

    @retry_assert
    async def assert_rule1_created():
        rules = await client.rss.rules()
        assert isinstance(rules, dict), "bad results"
        assert "rule1" in rules
        assert_rule(rules["rule1"])

    await assert_rule1_created()

    @retry_assert
    async def assert_rule2_removed():
        rules = await client.rss.rules()
        assert "rule2" not in rules

    await assert_rule2_removed()

    @retry_assert
    async def assert_rule3_renamed():
        rules = await client.rss.rules()
        assert "rule3" not in rules
        assert "rule3new" in rules
        assert_rule(rules["rule3new"])

    if APIVersion.compare(client.api_version, (2, 6, 1)) >= 0:
        # rename() is not working before API 2.6.1
        # See qbittorrent commit 1b5dd0aa2d2998934adc0dd1f1eb210dba3a9ae9
        await assert_rule3_renamed()

    await client.rss.remove_rule("rule1")
    await client.rss.remove_rule("rule3new")

    empty = await client.rss.rules()

    assert len(empty) == 0


@pytest.mark.asyncio
async def test_mark_as_read(client: APIClient):
    if APIVersion.compare(client.api_version, (2, 5, 1)) < 0:
        pytest.skip("API 2.5.1")

    ns = "marking"

    # no error will report even if feed does not exist.
    await client.rss.mark_as_read(rf"{ns}\news", "hello-world")
    await client.rss.mark_as_read(rf"{ns}\news")


@pytest.mark.asyncio
async def test_matching(client: APIClient, feed_service: FeedService):
    if APIVersion.compare(client.api_version, (2, 5, 1)) < 0:
        pytest.skip("API 2.5.1")

    ns = "matching"
    elements_url = f"{feed_service.url}/{ns}/elements.xml?count=12"
    news_url = f"{feed_service.url}/{ns}/news.xml?count=10"

    await client.rss.add_folder(ns)
    await client.rss.add_feed(elements_url, rf"{ns}\elements")
    await client.rss.add_feed(news_url, rf"{ns}\news")
    await client.rss.refresh_item(ns)

    rule_name = "matching-elements"
    rule = RSSRule(
        mustContain="gas", mustNotContain="hydrogen", affectedFeeds=[elements_url, news_url]
    )
    await client.rss.set_rule(rule_name, rule)

    @retry_assert
    async def assert_matching():
        elements_result = await client.rss.matching_articles(rule_name)
        assert isinstance(elements_result, dict)
        assert elements_result.keys() == {"elements"}
        assert isinstance(elements_result["elements"], list)
        assert all("gas" in s for s in elements_result["elements"])
        assert not any("hydrogen" in s for s in elements_result["elements"])

    await assert_matching()
    await client.rss.remove_item(ns)
    await client.rss.remove_rule(rule_name)
