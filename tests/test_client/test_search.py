from pathlib import Path
from typing import Any, List, Type, TypeVar

import pytest
from helper.lang import retry_assert
from typing_extensions import TypeGuard

from aioqbt.api.types import (
    SearchJobResults,
    SearchJobStatus,
    SearchPlugin,
    SearchPluginCategory,
    SearchResultEntry,
)
from aioqbt.client import APIClient

T = TypeVar("T")


@pytest.mark.asyncio
async def test_search(client: APIClient) -> None:
    # In this test, we install a plugin, do some search, and gather the result

    # install plugin
    # Assume the search plugin file is next to test file
    # and qBittorrent is running in the same file system.
    plugin_name = "linuxsearch"
    source = Path(__file__).with_name(f"{plugin_name}.py").as_uri()
    await client.search.install_plugin([source])

    @retry_assert
    async def plugin_installed() -> SearchPlugin:
        plugins = await client.search.plugins()

        assert isinstance(plugins, list)
        assert set([type(s) for s in plugins]) == {SearchPlugin}

        target = next((s for s in plugins if s.name == plugin_name), None)
        assert target is not None

        return target

    plugin = await plugin_installed()
    assert isinstance(plugin.enabled, bool)
    assert isinstance(plugin.fullName, str)
    assert isinstance(plugin.name, str)
    assert plugin.name == plugin_name
    assert isinstance(plugin.url, str)
    assert isinstance(plugin.version, str)
    assert isinstance(plugin.supportedCategories, list)
    assert len(plugin.supportedCategories)

    def list_type_guard(val: List[Any], tp: Type[T]) -> TypeGuard[List[T]]:
        category_types = set([type(s) for s in val])
        assert len(category_types) == 1
        return tp in category_types

    if list_type_guard(plugin.supportedCategories, SearchPluginCategory):
        # API 2.5.2 or higher
        assert "software" in set([s.id for s in plugin.supportedCategories])
    elif list_type_guard(plugin.supportedCategories, str):
        assert "software" in plugin.supportedCategories
    else:
        assert False, plugin.supportedCategories

    # start search
    search_start = await client.search.start("", [plugin_name], "all")
    assert isinstance(search_start.id, int)
    job_id = search_start.id

    # check status
    statuses = await client.search.status(job_id)
    assert isinstance(statuses, list)
    assert len(statuses) == 1
    assert isinstance(statuses[0], SearchJobStatus)
    assert isinstance(statuses[0].id, int)
    assert isinstance(statuses[0].status, str)
    assert statuses[0].status in {"Running", "Stopped"}
    assert isinstance(statuses[0].total, int)

    @retry_assert
    async def result_available():
        job = (await client.search.status(job_id))[0]
        assert job.total > 0

    await result_available()

    # check complete results
    complete = await client.search.results(job_id)
    assert isinstance(complete, SearchJobResults)
    assert isinstance(complete.status, str)
    assert complete.status in {"Running", "Stopped"}
    assert isinstance(complete.total, int)
    assert complete.total == 3
    assert isinstance(complete.results, list)
    assert len(complete.results) == complete.total
    assert set([type(s) for s in complete.results]) == {SearchResultEntry}

    # check limit results
    limited = await client.search.results(job_id, 1, 1)
    assert isinstance(limited, SearchJobResults)
    assert limited.total == complete.total
    assert len(limited.results) == 1
    assert limited.results == complete.results[1:2]

    # stop search
    await client.search.stop(job_id)

    @retry_assert
    async def job_stopped():
        statuses = await client.search.status(job_id)
        assert len(statuses) == 1
        assert statuses[0].status == "Stopped"

    await job_stopped()

    # delete search
    await client.search.delete(job_id)

    @retry_assert
    async def job_deleted():
        statuses = await client.search.status()
        assert job_id not in [s.id for s in statuses]

    await job_deleted()

    # uninstall plugin
    await client.search.uninstall_plugin([plugin_name])

    @retry_assert
    async def plugin_uninstalled():
        plugins = await client.search.plugins()
        assert plugin_name not in [s.name for s in plugins]

    await plugin_uninstalled()


@pytest.mark.asyncio
async def test_enable(client: APIClient) -> None:
    # no error response, even if plugin does not exist.
    await client.search.enable_plugin(["nonexistent"], False)


@pytest.mark.xfail(reason="Avoid internet access")
@pytest.mark.asyncio
async def test_update_plugins(client: APIClient) -> None:
    await client.search.update_plugins()
