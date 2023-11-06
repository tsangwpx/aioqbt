import json
from typing import TYPE_CHECKING, Dict, List, Mapping, Optional, Union

from aioqbt._paramdict import ParamDict
from aioqbt.api.types import RSSArticle, RSSFeed, RSSFolder, RSSRule
from aioqbt.client import APIGroup

if TYPE_CHECKING:
    from aioqbt.mapper import ObjectMapper

__all__ = ("RSSAPI",)

_KEY_UID = "uid"
_KEY_URL = "url"
_KEY_ARTICLES = "articles"


def _process_item(
    mapper: "ObjectMapper",
    context: Mapping[str, object],
    data: Dict[str, object],
) -> Union[RSSFeed, RSSFolder]:
    # As we recursively walk through the data
    # tree structure is created

    uid = data.get(_KEY_UID)
    url = data.get(_KEY_URL)

    if isinstance(uid, str) and isinstance(url, str):
        feed = mapper.create_object(RSSFeed, data, context)

        articles = data.get(_KEY_ARTICLES)
        if isinstance(articles, list):
            feed.articles = mapper.create_list(RSSArticle, articles, context)
        return feed
    else:
        items = {}

        for key, value in data.items():
            assert isinstance(value, dict)
            items[key] = _process_item(mapper, context, value)

        return RSSFolder(
            _items=items,
        )


class RSSAPI(APIGroup):
    """
    RSS APIs

    .. note::

        RSS API is experimental. Methods and results may change without notice.

    """

    async def add_folder(self, path: str) -> None:
        """
        Add a new folder.

        Raise :exc:`~.exc.ConflictError` if error.
        """
        data = ParamDict()
        data.required_str("path", path)

        await self._request_text(
            "POST",
            "rss/addFolder",
            data=data,
        )

    async def add_feed(self, url: str, path: str) -> None:
        """
        Add a new feed.

        Raise :exc:`~.exc.ConflictError` if error.
        """
        data = ParamDict()
        data.required_str("url", url)
        data.required_str("path", path)

        await self._request_text(
            "POST",
            "rss/addFeed",
            data=data,
        )

    async def remove_item(self, path: str) -> None:
        """
        Add a feed/folder.

        Raise :exc:`~.exc.ConflictError` if error.
        """
        data = ParamDict()
        data.required_str("path", path)

        await self._request_text(
            "POST",
            "rss/removeItem",
            data=data,
        )

    async def move_item(self, item_path: str, dest_path: str) -> None:
        """
        Move a feed/folder.

        Raise :exc:`~.exc.ConflictError` if error.
        """
        data = ParamDict()
        data.required_str("itemPath", item_path)
        data.required_str("destPath", dest_path)

        await self._request_text(
            "POST",
            "rss/moveItem",
            data=data,
        )

    async def items(self, with_data: Optional[bool] = None) -> RSSFolder:
        """
        Get the root folder, which consists of all feeds and sub-folders.

        If ``with_data=True``, feed title and a list of articles will also be available.
        See :class:`~.RSSFeed`.
        """
        params = ParamDict()
        params.optional_bool("withData", with_data)

        client = self._client()
        result = await client.request_json(
            "GET",
            "rss/items",
            params=params,
        )

        mapper = client._mapper
        context = client._context

        root = _process_item(mapper, context, result)

        assert isinstance(root, RSSFolder)
        return root

    async def mark_as_read(self, item_path: str, article_id: Optional[str] = None) -> None:
        """
        Mark an article as read.
        """
        # API 2.5.1
        data = ParamDict()
        data.required_str("itemPath", item_path)
        data.optional_str("articleId", article_id)

        await self._request_text(
            "POST",
            "rss/markAsRead",
            data=data,
        )

    async def refresh_item(self, item_path: str) -> None:
        """
        Refresh a folder/feed.
        """
        # API 2.2.1
        data = ParamDict()
        data.required_str("itemPath", item_path)

        await self._request_text(
            "POST",
            "rss/refreshItem",
            data=data,
        )

    async def set_rule(
        self,
        rule_name: str,
        rule_def: Union[str, RSSRule, Mapping[str, object]],
    ) -> None:
        """
        Add/update a rule.
        """
        if not isinstance(rule_def, str):
            rule_def = json.dumps(dict(rule_def), separators=(",", ":"))

        data = ParamDict()
        data.required_str("ruleName", rule_name)
        data.required_str("ruleDef", rule_def)

        await self._request_text(
            "POST",
            "rss/setRule",
            data=data,
        )

    async def rename_rule(self, rule_name: str, new_rule_name: str) -> None:
        """
        Rename a rule.

        .. note::

            Before API 2.6.1, there was a bug that
            renaming rule would not change the result of :meth:`~.RSSAPI.rules`.

        """
        data = ParamDict()
        data.required_str("ruleName", rule_name)
        data.required_str("newRuleName", new_rule_name)

        await self._request_text(
            "POST",
            "rss/renameRule",
            data=data,
        )

    async def remove_rule(self, rule_name: str) -> None:
        """
        Remove a rule.
        """
        data = ParamDict()
        data.required_str("ruleName", rule_name)

        await self._request_text(
            "POST",
            "rss/removeRule",
            data=data,
        )

    async def rules(self) -> Dict[str, RSSRule]:
        """
        Get all rules.
        """
        return await self._request_json(  # type: ignore[no-any-return]
            "GET",
            "rss/rules",
        )

    async def matching_articles(self, rule_name: str) -> Dict[str, List[str]]:
        """
        Get articles matched by a rule.

        The result is a dict mapping feed names to lists of article titles.
        """
        # API 2.5.1
        params = ParamDict()
        params.required_str("ruleName", rule_name)

        return await self._request_json(  # type: ignore[no-any-return]
            "GET",
            "rss/matchingArticles",
            params=params,
        )
