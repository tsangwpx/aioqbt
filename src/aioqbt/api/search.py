from typing import Any, Dict, Iterable, List, Optional, Union

from typing_extensions import Literal

from aioqbt._paramdict import ParamDict
from aioqbt.api.types import (
    SearchJobResults,
    SearchJobStart,
    SearchJobStatus,
    SearchPlugin,
    SearchPluginCategory,
    SearchResultEntry,
)
from aioqbt.client import APIGroup
from aioqbt.version import APIVersion


class SearchAPI(APIGroup):
    """
    Search APIs.

    .. note::

        Search API is experimental. Methods and results may change without notice.

    """

    async def start(
        self,
        pattern: str,
        plugins: Union[List[str], Literal["all"], Literal["enabled"]],
        category: Union[str, Literal["all"]],
    ) -> SearchJobStart:
        """
        Start a search job.

        The result consists of only the search job :attr:`~.SearchJobStart.id`.

        :param pattern: Search pattern.
        :param plugins: Plugins used in search. Special values:
            ``all`` uses all plugins while ``enabled`` uses enabled plugins only.
        :param category: Search specific category or ``all``.

        :raises ~exc.ConflictError: if error.
        """
        data = ParamDict()
        data.required_str("pattern", pattern)
        data.required_list("plugins", plugins, "|")
        data.required_str("category", category)

        return await self._request_mapped_object(
            SearchJobStart,
            "POST",
            "search/start",
            data=data,
        )

    async def stop(self, id: int) -> None:
        """
        Stop a search job.

        :raises ~exc.NotFoundError: if the search job is not found.
        """
        data = ParamDict()
        data.required_int("id", id)

        await self._request_text(
            "POST",
            "search/stop",
            data=data,
        )

    async def status(self, id: Optional[int] = None) -> List[SearchJobStatus]:
        """
        Query search job statuses.

        :raises ~exc.NotFoundError: if the search job is specified but not found.
        """
        params = ParamDict()
        params.optional_int("id", id)

        return await self._request_mapped_list(
            SearchJobStatus,
            "GET",
            "search/status",
            params=params,
        )

    async def results(
        self,
        id: int,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> SearchJobResults:
        """
        Get search job results.

        :raises ~exc.NotFoundError: if the search job is not found.
        :raises ~exc.ConflictError: if ``offset`` is out of range.
        """

        params = ParamDict()
        params.required_int("id", id)
        params.optional_int("limit", limit)
        params.optional_int("offset", offset)

        client = self._client()

        data = await client.request_json(
            "GET",
            "search/results",
            params=params,
        )

        mapper = client._mapper
        context = client._context
        ret = mapper.create_object(SearchJobResults, data, context)
        ret.results = mapper.create_list(SearchResultEntry, data["results"], context)

        return ret

    async def delete(self, id: int) -> None:
        """
        Delete a search job.

        :raises ~exc.NotFoundError: if the search job is not found.
        """
        data = ParamDict()
        data.required_int("id", id)

        await self._request_text(
            "POST",
            "search/delete",
            data=data,
        )

    async def plugins(self) -> List[SearchPlugin]:
        """
        Get all plugins.
        """
        client = self._client()

        data: List[Dict[str, object]] = await client.request_json(
            "GET",
            "search/plugins",
        )

        mapper = client._mapper
        context = client._context

        result: List[SearchPlugin] = mapper.create_list(SearchPlugin, data, context)

        plugin: SearchPlugin
        plugin_data: Dict[str, Any]

        dict_list = True

        if APIVersion.compare(client.api_version, (2, 5, 2)) < 0:
            # before API 2.5.2 ~= v4.3.0alpha1
            # supportedCategories is a list of localized category name strings
            # see commit 8e8cd59d90e63b992bc5c43c29d5aec001855a4e
            for plugin in result:
                if any(isinstance(s, str) for s in plugin.supportedCategories):
                    dict_list = False
                    break

        if dict_list:
            for plugin, plugin_data in zip(result, data):
                plugin.supportedCategories = mapper.create_list(
                    SearchPluginCategory,
                    plugin_data["supportedCategories"],  # type: ignore[arg-type]
                    context,
                )

        return result

    async def install_plugin(self, sources: Iterable[str]) -> None:
        """
        Install plugins.
        """
        data = ParamDict()
        data.required_list("sources", sources, "|")

        await self._request_text(
            "POST",
            "search/installPlugin",
            data=data,
        )

    async def uninstall_plugin(self, names: Iterable[str]) -> None:
        """
        Uninstall plugins.
        """
        data = ParamDict()
        data.required_list("names", names, "|")

        await self._request_text(
            "POST",
            "search/uninstallPlugin",
            data=data,
        )

    async def enable_plugin(self, names: Iterable[str], enable: bool) -> None:
        """
        Enable/disable plugins.

        :param names: a list of plugins to enable/disable.
        :param enable: ``True`` to enable or ``False`` to disable.
        """
        data = ParamDict()
        data.required_list("names", names, "|")
        data.required_bool("enable", enable)

        await self._request_text(
            "POST",
            "search/enablePlugin",
            data=data,
        )

    async def update_plugins(self) -> None:
        """
        Update plugins.
        """
        await self._request_text(  # pragma: no cover
            "POST",
            "search/updatePlugins",
        )
