import dataclasses
import os
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Tuple, Union, overload

import aiohttp
from typing_extensions import Self

from aioqbt import exc
from aioqbt._decorator import copy_self
from aioqbt._paramdict import ParamDict
from aioqbt.api.types import (
    Category,
    ContentLayout,
    FileEntry,
    InfoFilter,
    RatioLimitTypes,
    SeedingTimeLimitTypes,
    StopCondition,
    TorrentInfo,
    TorrentProperties,
    Tracker,
    WebSeed,
)
from aioqbt.bittorrent import InfoHash, InfoHashes, InfoHashesOrAll, get_info_hash
from aioqbt.chrono import TimeUnit
from aioqbt.client import APIClient, APIGroup, since, virtual
from aioqbt.typing import StrPath
from aioqbt.version import APIVersion, ClientVersion, param_version_check, version_check

__all__ = (
    "AddFormBuilder",
    "TorrentsAPI",
)


def _check_iterable_except_str(param: str, value: Iterable[Any]):
    """Explicitly reject ``str`` as ``Iterable[str]``"""
    if isinstance(value, str):  # pragma: no cover
        raise ValueError(f"{param!r} refused str as iterable")


class TorrentsAPI(APIGroup):
    """
    API methods under ``torrents``.
    """

    async def info(
        self,
        filter: Optional[str] = None,
        category: Optional[str] = None,
        sort: Optional[str] = None,
        reverse: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        hashes: Optional[InfoHashesOrAll] = None,
        tag: Optional[str] = None,  # since API v2.8.3
    ) -> List[TorrentInfo]:
        """
        Get a list of :class:`.TorrentInfo`.

        To obtain a list of completed torrents sorted by name::

            torrents = await client.torrents.info(
                filter=InfoFilter.COMPLETED,
                sort="name",
            )

        See also :APIWiki:`torrents/info <#get-torrent-list>`
        for filter and result meanings.

        :param filter: State filter: :class:`.InfoFilter` or ``str``.
        :param category: category filter.
        :param sort: Sort results by an attribute/field.
        :param reverse: Reverse the results.
        :param limit: Maximum number of returned results.
        :param offset: Results starting from the ``offset``-th torrents.
        :param hashes: A list of info hashes, or a str ``all``.
        :param tag: Tag filter.
        """
        if isinstance(filter, InfoFilter):
            filter = str(filter)

        if hashes is None:
            params = ParamDict()
        else:
            params = ParamDict.with_hashes(hashes)

        params.optional_str("filter", filter)
        params.optional_str("category", category)
        params.optional_str("sort", sort)
        params.optional_bool("reverse", reverse)
        params.optional_int("limit", limit)
        params.optional_int("offset", offset)

        if tag is not None:
            param_version_check("tag", self._client().api_version, (2, 8, 3))
            params.optional_str("tag", tag)

        return await self._request_mapped_list(
            TorrentInfo,
            "GET",
            "torrents/info",
            params=params,
        )

    async def properties(self, hash: InfoHash) -> TorrentProperties:
        """Get properties of a torrent."""

        props = await self._request_mapped_object(
            TorrentProperties,
            "GET",
            "torrents/properties",
            params=ParamDict.with_hash(hash),
        )

        if not hasattr(props, "hash"):
            props.hash = get_info_hash(hash)

        return props

    async def trackers(self, hash: InfoHash) -> List[Tracker]:
        """Trackers in a torrent."""

        # Tracker's status may be a string or int, API v2.2.0
        return await self._request_mapped_list(
            Tracker,
            "GET",
            "torrents/trackers",
            params=ParamDict.with_hash(hash),
        )

    async def webseeds(self, hash: InfoHash) -> List[WebSeed]:
        """Web seeds in a torrent."""
        return await self._request_mapped_list(
            WebSeed,
            "GET",
            "torrents/webseeds",
            params=ParamDict.with_hash(hash),
        )

    async def files(
        self,
        hash: InfoHash,
        indexes: Optional[Iterable[int]] = None,
    ) -> List[FileEntry]:
        """Files in a torrent."""
        params = ParamDict.with_hash(hash)

        if indexes is not None:
            param_version_check("indexes", self._client().api_version, (2, 8, 2))
            params.optional_list("indexes", indexes, "|")

        return await self._request_mapped_list(
            FileEntry,
            "GET",
            "torrents/files",
            params=params,
        )

    async def piece_states(self, hash: InfoHash) -> List[int]:
        """
        A list of piece states in a torrent.

        To compare results, use following constants from :class:`~.PieceState` enum:

        * :attr:`.PieceState.UNAVAILABLE`
        * :attr:`.PieceState.DOWNLOADING`
        * :attr:`.PieceState.DOWNLOADED`

        """
        return await self._request_json(
            "GET",
            "torrents/pieceStates",
            params=ParamDict.with_hash(hash),
        )

    async def piece_hashes(self, hash: InfoHash) -> List[str]:
        """
        A list of piece hashes in a torrent.
        """

        return await self._request_json(
            "GET",
            "torrents/pieceHashes",
            params=ParamDict.with_hash(hash),
        )

    async def pause(self, hashes: InfoHashesOrAll):
        """
        Pause torrents.

        Torrents can be specified by their info hashes.
        Passing ``all`` pauses all torrents.

        """

        await self._request_text(
            "POST",
            "torrents/pause",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def resume(self, hashes: InfoHashesOrAll):
        """
        Resume torrents.

        Torrents can be specified by their info hashes.
        Passing ``all`` resumes all torrents.

        """

        await self._request_text(
            "POST",
            "torrents/resume",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def delete(self, hashes: InfoHashesOrAll, delete_files: bool):
        """
        Delete torrents.

        Torrents can be specified by their info hashes.
        Passing ``all`` deletes all torrents.

        Pass ``True`` to ``delete_files`` to remove downloaded content.
        """

        if hashes != "all":
            _check_iterable_except_str("hashes", hashes)

        data = ParamDict.with_hashes_or_all(hashes)
        data.required_bool("deleteFiles", delete_files)  # default to False

        await self._request_text(
            "POST",
            "torrents/delete",
            data=data,
        )

    async def recheck(self, hashes: InfoHashesOrAll):
        """Recheck torrents."""

        await self._request_text(
            "POST",
            "torrents/recheck",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def reannounce(self, hashes: InfoHashesOrAll):
        """Reannounce torrents."""

        # since API v2.0.2

        await self._request_text(
            "POST",
            "torrents/reannounce",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def add(self, form: aiohttp.FormData):
        """
        Add torrents by URLs, info hashes, and/or file blobs.

        See :class:`.AddFormBuilder` on how to configure and build
        :class:`~aiohttp.FormData` to submit.

        .. note::

            :exc:`~.exc.AddTorrentError` may raise if no *new* torrents
            are added.

        :param form: form data to submit.
        """

        resp = await self._request(
            "POST",
            "torrents/add",
            data=form,
        )

        async with resp:
            body = await resp.read()

            if body != b"Ok.":
                ex = exc.AddTorrentError.from_response(resp)
                ex.message = body.decode("utf-8")
                raise ex

    async def add_trackers(self, hash: InfoHash, trackers: Iterable[str]):
        _check_iterable_except_str("trackers", trackers)

        data = ParamDict.with_hash(hash)
        data.required_list("urls", trackers, "\n")

        await self._request_text(
            "POST",
            "torrents/addTrackers",
            data=data,
        )

    @since((2, 2, 0))
    async def edit_tracker(
        self,
        hash: InfoHash,
        orig_url: str,
        new_url: str,
    ):
        data = ParamDict.with_hash(hash)
        data.required_str("origUrl", orig_url)
        data.required_str("newUrl", new_url)

        await self._request_text(
            "POST",
            "torrents/editTracker",
            data=data,
        )

    async def remove_trackers(self, hash: InfoHash, urls: Iterable[str]):
        _check_iterable_except_str("urls", urls)

        # Since API v2.2.0
        data = ParamDict.with_hash(hash)
        data.required_list("urls", urls, "|")

        await self._request_text(
            "POST",
            "torrents/removeTrackers",
            data=data,
        )

    async def add_peers(self, hashes: InfoHashes, peers: Iterable[str]):
        _check_iterable_except_str("peers", peers)

        data = ParamDict.with_hashes(hashes)
        data.required_list("peers", peers, "|")

        await self._request_text(
            "POST",
            "torrents/addPeers",
            data=data,
        )

    async def top_prio(self, hashes: InfoHashesOrAll):
        await self._request_text(
            "POST",
            "torrents/topPrio",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def bottom_prio(self, hashes: InfoHashesOrAll):
        await self._request_text(
            "POST",
            "torrents/bottomPrio",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def increase_prio(self, hashes: InfoHashesOrAll):
        await self._request_text(
            "POST",
            "torrents/increasePrio",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def decrease_prio(self, hashes: InfoHashesOrAll):
        await self._request_text(
            "POST",
            "torrents/decreasePrio",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def file_prio(self, hash: InfoHash, id: Iterable[int], priority: int):
        """
        Prioritize files in a torrent.

        :param hash: Info hash
        :param id: A list of file indices to prioritize.
        :param priority: Priority, :class:`.FilePriority`.
        """

        # id may be a list since API v2.2.0
        if isinstance(id, int):
            id = (id,)
        data = ParamDict.with_hash(hash)
        data.required_list("id", id, "|")
        data.required_int("priority", priority)

        await self._request_text(
            "POST",
            "torrents/filePrio",
            data=data,
        )

    async def download_limit(self, hashes: InfoHashesOrAll) -> Dict[str, int]:
        """
        Get torrent download limits.

        The result is a dict mapping info hash to download speed limit
        in bytes/second.

        :param hashes: A list of info hashes or ``all`` for all torrents.
        """
        params = ParamDict.with_hashes_or_all(hashes)
        result = await self._request_json(
            "GET",
            "torrents/downloadLimit",
            params=params,
        )
        return result

    async def set_download_limit(self, hashes: InfoHashesOrAll, limit: int):
        """
        Update torrent download limits.

        :param hashes: A list of info hashes or ``all`` for all torrents.
        :param limit: Download limit in bytes/second.
        """

        data = ParamDict.with_hashes_or_all(hashes)
        data.required_int("limit", limit)

        await self._request_text(
            "POST",
            "torrents/setDownloadLimit",
            data=data,
        )

    async def set_share_limits(
        self,
        hashes: InfoHashesOrAll,
        ratio_limit: RatioLimitTypes,
        seeding_time_limit: SeedingTimeLimitTypes,
    ):
        """
        Set share limits for torrents.

        :param hashes: A list of info hashes or ``all`` for all torrents.
        :param ratio_limit: A number or :attr:`.RatioLimits.UNSET`.
        :param seeding_time_limit: :class:`~datetime.timedelta`, or
                :class:`.SeedingTimeLimits` constants.
        """
        # since API v2.0.1

        data = ParamDict.with_hashes_or_all(hashes)
        data.required_float("ratioLimit", ratio_limit)
        data.required_duration("seedingTimeLimit", seeding_time_limit, TimeUnit.MINUTES)

        await self._request_text(
            "POST",
            "torrents/setShareLimits",
            data=data,
        )

    async def upload_limit(self, hashes: InfoHashesOrAll) -> Dict[str, int]:
        """
        Get torrent upload limits.

        The result is a dict mapping info hash to upload speed limit
        in bytes/second.

        :param hashes: A list of info hashes or ``all`` for all torrents.
        """
        params = ParamDict.with_hashes_or_all(hashes)

        return await self._request_json(
            "GET",
            "torrents/uploadLimit",
            params=params,
        )

    async def set_upload_limit(self, hashes: InfoHashesOrAll, limit: int):
        """
        Update torrent upload limits.

        :param hashes: A list of info hashes or ``all`` for all torrents.
        :param limit: Upload limit in bytes/second.
        """
        data = ParamDict.with_hashes_or_all(hashes)
        data.required_int("limit", limit)

        await self._request_text(
            "POST",
            "torrents/setUploadLimit",
            data=data,
        )

    async def set_location(
        self,
        hashes: InfoHashesOrAll,
        location: StrPath,
    ):
        """
        Change location (save path) for torrents.

        This method also turns off auto torrent management (AutoTMM)
        for torrents.

        See also :meth:`~.set_save_path`.

        :param hashes: A list of info hashes or ``all`` for all torrents.
        :param location: Location.
        """
        data = ParamDict.with_hashes_or_all(hashes)
        data.required_path("location", location)

        await self._request_text(
            "POST",
            "torrents/setLocation",
            data=data,
        )

    async def set_save_path(
        self,
        id: InfoHashesOrAll,
        path: StrPath,
    ):
        """
        Change save path (location) for torrents.

        This method causes no effect to torrents with auto torrent
        management (AutoTMM) enabled.

        Available since qBittorrent v4.4.0.

        See also :meth:`~.set_location`.

        :param id: A list of info hashes or ``all`` for all torrents.
        :param path: Save path.
        """
        # since API v2.8.4
        data = ParamDict.with_hashes_or_all(id, key="id")
        data.required_path("path", path)

        await self._request_text(
            "POST",
            "torrents/setSavePath",
            data=data,
        )

    async def set_download_path(
        self,
        id: InfoHashesOrAll,
        path: StrPath,
    ):
        """
        Change download path for torrents.

        Available since qBittorrent v4.4.0.

        :param id: A list of info hashes or ``all`` for all torrents.
        :param path: Download path.
        """
        # since API v2.8.4
        data = ParamDict.with_hashes_or_all(id, key="id")
        data.required_path("path", path)

        await self._request_text(
            "POST",
            "torrents/setDownloadPath",
            data=data,
        )

    async def rename(self, hash: InfoHash, name: str):
        """Rename a torrent."""
        data = ParamDict.with_hash(hash)
        data.required_str("name", name)

        await self._request_text(
            "POST",
            "torrents/rename",
            data=data,
        )

    async def set_category(self, hashes: InfoHashesOrAll, category: str):
        """
        Change torrents' category.

        :param hashes: A list of info hashes or ``all`` for all torrents.
        :param category: Category name. An empty string indicates no category.
        """

        params = ParamDict.with_hashes_or_all(hashes)
        params.required_str("category", category)

        await self._request_text(
            "POST",
            "torrents/setCategory",
            data=params,
        )

    # since API v2.1.1
    async def categories(self) -> Dict[str, Category]:
        """
        Get categories.

        A dict mapping category name to :class:`.Category` is returned.
        """
        return await self._request_mapped_dict(
            Category,
            "GET",
            "torrents/categories",
        )

    async def create_category(self, category: str, save_path: StrPath):
        """Create category."""
        data = ParamDict()
        data.required_str("category", category)
        data.required_path("savePath", save_path)

        await self._request_text(
            "POST",
            "torrents/createCategory",
            data=data,
        )

    async def edit_category(self, category: str, save_path: StrPath):
        """Edit category."""
        # since API v2.1.0
        # empty save_path ("") is default save path

        data = ParamDict()
        data.required_str("category", category)
        data.required_path("savePath", save_path)

        await self._request_text(
            "POST",
            "torrents/editCategory",
            data=data,
        )

    async def remove_categories(self, categories: Iterable[str]):
        """Remove category."""
        _check_iterable_except_str("categories", categories)

        data = ParamDict()
        data.required_list("categories", categories, "\n")

        await self._request_text(
            "POST",
            "torrents/removeCategories",
            data=data,
        )

    @since((2, 3, 0))
    async def add_tags(self, hashes: InfoHashesOrAll, tags: Iterable[str]):
        _check_iterable_except_str("tags", tags)

        data = ParamDict.with_hashes_or_all(hashes)
        data.required_list("tags", tags, ",")

        await self._request_text(
            "POST",
            "torrents/addTags",
            data=data,
        )

    @since((2, 3, 0))
    async def remove_tags(self, hashes: InfoHashesOrAll, tags: Iterable[str]):
        _check_iterable_except_str("tags", tags)

        data = ParamDict.with_hashes_or_all(hashes)
        data.required_list("tags", tags, ",")
        await self._request_text(
            "POST",
            "torrents/removeTags",
            data=data,
        )

    @since((2, 3, 0))
    async def tags(self) -> List[str]:
        return await self._request_json(
            "GET",
            "torrents/tags",
        )

    @since((2, 3, 0))
    async def create_tags(self, tags: Iterable[str]):
        _check_iterable_except_str("tags", tags)

        data = ParamDict()
        data.required_list("tags", tags, ",")
        await self._request_text(
            "POST",
            "torrents/createTags",
            data=data,
        )

    @since((2, 3, 0))
    async def delete_tags(self, tags: Iterable[str]):
        _check_iterable_except_str("tags", tags)

        data = ParamDict()
        data.required_list("tags", tags, ",")
        await self._request_text(
            "POST",
            "torrents/deleteTags",
            data=data,
        )

    async def set_auto_management(self, hashes: InfoHashesOrAll, enable: bool):
        data = ParamDict.with_hashes_or_all(hashes)
        data.optional_bool("enable", enable)

        await self._request_text(
            "POST",
            "torrents/setAutoManagement",
            data=data,
        )

    async def toggle_sequential_download(self, hashes: InfoHashesOrAll):
        """Flip ``seq_dl`` values for torrents."""
        data = ParamDict.with_hashes_or_all(hashes)

        await self._request_text(
            "POST",
            "torrents/toggleSequentialDownload",
            data=data,
        )

    @virtual
    async def set_sequential_download(self, hashes: InfoHashesOrAll, value: bool):
        """
        Change ``seq_dl`` for torrents.

        .. note::

            This method is implemented by querying torrent ``seq_dl`` values, and
            :meth:`toggling <.TorrentsAPI.toggle_sequential_download>` them if needed.

        """
        torrents = await self.info(hashes=hashes)
        targets = []

        for info in torrents:
            if info.seq_dl != value:
                targets.append(info.hash)

        if targets:
            await self.toggle_sequential_download(targets)

    async def toggle_first_last_piece_prio(self, hashes: InfoHashesOrAll):
        """Flip ``f_l_piece_prio`` values for torrents."""
        await self._request_text(
            "POST",
            "torrents/toggleFirstLastPiecePrio",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    @virtual
    async def set_first_last_piece_prio(self, hashes: InfoHashesOrAll, value: bool):
        """
        Change ``f_l_piece_prio`` for torrents.

        .. note::

            This method is implemented by querying torrent ``f_l_piece_prio`` values, and
            :meth:`toggling <.TorrentsAPI.toggle_first_last_piece_prio>` them if needed.

        """
        torrents = await self.info(hashes=hashes)
        targets = []

        for info in torrents:
            if info.f_l_piece_prio != value:
                targets.append(info.hash)

        if targets:
            await self.toggle_first_last_piece_prio(targets)

    async def set_force_start(self, hashes: InfoHashesOrAll, force: bool):
        """Set ``force_start`` flags for torrents."""
        data = ParamDict.with_hashes_or_all(hashes)
        data.required_bool("value", force)

        await self._request_text(
            "POST",
            "torrents/setForceStart",
            data=data,
        )

    async def set_super_seeding(self, hashes: InfoHashesOrAll, value: bool):
        """Set ``super_seeding`` flags for torrents."""
        data = ParamDict.with_hashes_or_all(hashes)
        # default value (invalid value) is treated as false
        data.required_bool("value", value)

        await self._request_text(
            "POST",
            "torrents/setSuperSeeding",
            data=data,
        )

    @overload
    async def rename_file(self, hash: InfoHash, id: int, name: str):
        """available until client 4.3.3"""

    @overload
    async def rename_file(self, hash: InfoHash, old_path: str, new_path: str):
        """available since client 4.3.3 or API 2.7.0"""

    @since((2, 4, 0))
    async def rename_file(self, hash, arg, arg2):
        """
        Rename a file in torrent.

        On qBittorrent v4.3.3 or later, the signature is ``rename_file(hash, old_path, new_path)``.

        Below qBittorrent v4.3.3, use ``rename_file(hash, id, name)``, where ``id`` is
        the file index from :meth:`~.TorrentsAPI.files`.

        Available since qBittorrent v4.2.1 (API 2.4.0).

        Signature changed in v4.3.3 (API 2.7.0).

        See also: https://github.com/qbittorrent/qBittorrent/pull/13995

        """
        version_check(self._client().api_version, (2, 4, 0))

        data = ParamDict.with_hash(hash)
        if isinstance(arg, str):
            data.required_str("oldPath", arg)
            data.required_str("newPath", arg2)
        elif isinstance(arg, int):
            data.required_int("id", arg)
            data.required_str("name", arg2)
        else:
            raise TypeError(f"Bad call signature: ({type(hash)!r}, {type(arg)!r}, {type(arg2)!r})")

        await self._request_text(
            "POST",
            "torrents/renameFile",
            data=data,
        )

    @since((2, 8, 0))
    async def rename_folder(self, hash: InfoHash, old_path: str, new_path: str):
        """Rename a folder."""
        version_check(self._client().api_version, (2, 8, 0))

        data = ParamDict.with_hash(hash)
        data.required_path("oldPath", old_path)
        data.required_path("newPath", new_path)

        await self._request_text(
            "POST",
            "torrents/renameFolder",
            data=data,
        )

    async def export(self, hash: InfoHash) -> bytes:
        """Export a torrent as ``bytes``."""
        # since API v2.8.11

        params = ParamDict.with_hash(hash)
        resp = await self._client().request(
            "GET",
            "torrents/export",
            params=params,
        )

        async with resp:
            return await resp.read()


@dataclass
class AddFormBuilder:
    """
    Build :class:`~aiohttp.FormData` used in :meth:`.TorrentsAPI.add`.

    Most builder methods return a modified copy of itself.
    Method chaining is desirable to generate the final :class:`~aiohttp.FormData`.

    Here is an example to illustrate the usage::

        # Create AddFormBuilder from a particular client
        builder = AddFormBuilder.with_client(client)

        # Set torrent category to "linux"
        builder = builder.category("linux")

        # Set ratio limit to 10
        builder = builder.ratio_limit(10)

        # Add a torrent by its info hash (debian-11.7.0-amd64-netinst.iso)
        builder = builder.include_url("6f84758b0ddd8dc05840bf932a77935d8b5b8b93")

        # Add a torrent by URL/magnet link (debian-11.6.0-amd64-netinst.iso)
        magnet_link = "magnet:?xt=urn:btih:6d4795dee70aeb88e03e5336ca7c9fcf0a1e206d"
        builder = builder.include_url(magnet_link)

        # Upload a torrent with its bytes data and name
        builder = builder.include_url(file_bytes, "debian-12.0.0-amd64-netinst.iso")

        # Generate FormData object
        form = builder.build()

        # Add torrents to client
        await client.torrents.add(form)

    See also :APIWiki:`torrents/add <#add-new-torrent>`.

    """

    client_version: Optional[ClientVersion] = None
    api_version: Optional[APIVersion] = None

    _urls: List[str] = field(default_factory=list)
    _files: List[Tuple[bytes, str]] = field(default_factory=list)

    _savepath: Optional[str] = None
    _download_path: Optional[str] = None
    _use_download_path: Optional[bool] = None
    _cookie: Optional[str] = None
    _category: Optional[str] = None
    _tags: Optional[str] = None
    _skip_checking: Optional[bool] = None
    _paused: Optional[bool] = None
    _root_folder: Optional[bool] = None
    _rename: Optional[str] = None
    _up_limit: Optional[int] = None
    _dl_limit: Optional[int] = None
    _ratio_limit: Optional[float] = None
    _seeding_time_limit: Optional[int] = None
    _auto_tmm: Optional[bool] = None
    _sequential_download: Optional[bool] = None
    _first_last_piece_prio: Optional[bool] = None
    _stop_condition: Optional[str] = None
    _content_layout: Optional[str] = None

    def __deepcopy__(self, memodict=None):
        return dataclasses.replace(
            self,
            _urls=list(self._urls),
            _files=list(self._files),
        )

    __copy__ = __deepcopy__

    @copy_self
    def include_url(self, url: str) -> Self:
        """
        Add a URL, magnet link, or info hash (SHA1/SHA256) to form.
        """

        self._urls.append(url)
        return self

    @copy_self
    def include_file(self, data: bytes, filename: Optional[str] = None) -> Self:
        """
        Add a torrent file to form.
        """

        if filename is None:
            filename = f"{len(self._files) + 1:d}.torrent"

        self._files.append((bytes(data), filename))
        return self

    def add_url(self, url: str) -> Self:
        """deprecated, use :meth:`.include_url` instead."""
        # deprecated, use include_url() instead
        return self.include_url(url)  # pragma: no cover

    def add_torrent(self, filename: str, data: bytes) -> Self:
        """deprecated, use :meth:`.include_file` instead."""
        return self.include_file(data, filename)  # pragma: no cover

    @copy_self
    def savepath(self, savepath: StrPath) -> Self:
        """Set ``savepath`` value."""
        self._savepath = _convert_path(savepath)
        return self

    @copy_self
    def download_path(self, download_path: StrPath) -> Self:
        """
        Set ``downloadPath`` value.

        Also use :meth:`use_download_path(True) <.use_download_path>` to enable download path.
        """
        # API v2.8.4
        self._download_path = _convert_path(download_path)
        return self

    @copy_self
    def use_download_path(self, use_download_path: bool) -> Self:
        """
        Set ``useDownloadPath`` value.
        """
        # API v2.8.4
        self._use_download_path = use_download_path
        return self

    @copy_self
    def cookie(self, cookie: str) -> Self:
        """Set ``cookie`` value."""
        self._cookie = cookie
        return self

    @copy_self
    def category(self, category: str) -> Self:
        """Set ``category`` value."""
        self._category = category
        return self

    @copy_self
    def tags(self, tags: Iterable[str]) -> Self:
        """
        Associate torrents being added with tags.

        Available since API v2.6.2.

        :param tags: list of tags.
        """

        version_check(self.api_version, (2, 6, 2))
        _check_iterable_except_str("tags", tags)

        tags = list(tags)
        parts = []
        for item in tags:
            if not isinstance(item, str):
                raise ValueError("each tag must be a str")
            if "," in item:
                raise ValueError(f"Tag cannot contain comma: {item!r}")
            parts.append(item)

        self._tags = ",".join(parts)
        return self

    @copy_self
    def skip_checking(self, skip_checking: bool) -> Self:
        """Set ``skip_checking`` value."""
        self._skip_checking = skip_checking
        return self

    @copy_self
    def paused(self, paused: bool) -> Self:
        """Set ``paused`` value."""
        self._paused = paused
        return self

    @copy_self
    def root_folder(self, root_folder: bool) -> Self:
        """
        Set ``root_folder`` value.

        Removed on qBittorrent v4.3.2 and later. Use :meth:`.content_layout` instead.
        """
        self._root_folder = root_folder
        return self

    @copy_self
    def rename(self, rename: str) -> Self:
        """Set ``rename`` value, which is the new torrent name."""
        self._rename = rename
        return self

    @copy_self
    def up_limit(self, up_limit: int) -> Self:
        """Set ``upLimit`` in bytes/s"""
        self._up_limit = up_limit
        return self

    @copy_self
    def dl_limit(self, dl_limit: int) -> Self:
        """Set ``dlLimit`` in bytes/s"""
        self._dl_limit = dl_limit
        return self

    @copy_self
    @since((2, 8, 1))
    def ratio_limit(self, ratio_limit: RatioLimitTypes) -> Self:
        """Set ``ratioLimit`` value."""
        version_check(self.api_version, (2, 8, 1))
        self._ratio_limit = float(ratio_limit)
        return self

    @copy_self
    @since((2, 8, 1))
    def seeding_time_limit(self, seeding_time_limit: SeedingTimeLimitTypes) -> Self:
        """Set ``seedingTimeLimit`` value."""
        version_check(self.api_version, (2, 8, 1))
        self._seeding_time_limit = int(_convert_duration(seeding_time_limit, TimeUnit.MINUTES))
        return self

    @copy_self
    def auto_tmm(self, auto_tmm: bool) -> Self:
        """Set ``autoTMM`` value."""
        self._auto_tmm = auto_tmm
        return self

    @copy_self
    def sequential_download(self, sequential_download: bool) -> Self:
        """Set ``sequentialDownload`` value."""
        self._sequential_download = sequential_download
        return self

    @copy_self
    def first_last_piece_prio(self, first_last_piece_prio: bool) -> Self:
        """Set ``firstLastPiecePrio`` value."""
        self._first_last_piece_prio = first_last_piece_prio
        return self

    @copy_self
    def stop_condition(self, stop_condition: StopCondition) -> Self:
        """Set ``stopCondition`` value."""
        # API v2.8.15
        self._stop_condition = str(stop_condition)
        return self

    @copy_self
    def content_layout(self, content_layout: ContentLayout) -> Self:
        """Set ``contentLayout`` value."""
        # API v2.7.0
        self._content_layout = str(content_layout)
        return self

    def build(self) -> aiohttp.FormData:
        """
        Build :class:`~aiohttp.FormData`.
        """

        def bool_str(b: bool):
            """boolean to lowercase string"""
            return "true" if b else "false"

        form = aiohttp.FormData()

        if self._urls:
            # XXX: urllib.parse.quote may be useful to escape character.
            # Probably 4.1.6???
            form.add_field("urls", "\n".join(self._urls), content_type="text/plain")

        for filedata, filename in self._files:
            form.add_field(
                "torrents",
                filedata,
                filename=filename,
                content_type="application/x-bittorrent",
            )

        if self._savepath is not None:
            form.add_field("savepath", self._savepath)

        if self._download_path is not None:
            form.add_field("downloadPath", self._download_path)

        if self._use_download_path is not None:
            form.add_field("useDownloadPath", bool_str(self._use_download_path))

        if self._cookie is not None:
            form.add_field("cookie", self._cookie)

        if self._category is not None:
            form.add_field("category", self._category)

        if self._skip_checking is not None:
            form.add_field("skip_checking", bool_str(self._skip_checking))

        if self._paused is not None:
            form.add_field("paused", bool_str(self._paused))

        if self._root_folder is not None:
            form.add_field("root_folder", bool_str(self._root_folder))

        if self._rename is not None:
            form.add_field("rename", self._rename)

        if self._up_limit is not None:
            form.add_field("upLimit", str(self._up_limit))

        if self._dl_limit is not None:
            form.add_field("dlLimit", str(self._dl_limit))

        if self._ratio_limit is not None:
            form.add_field("ratioLimit", str(self._ratio_limit))

        if self._seeding_time_limit is not None:
            form.add_field("seedingTimeLimit", str(self._seeding_time_limit))

        if self._auto_tmm is not None:
            form.add_field("autoTMM", bool_str(self._auto_tmm))

        if self._sequential_download is not None:
            form.add_field("sequentialDownload", bool_str(self._sequential_download))

        if self._first_last_piece_prio is not None:
            form.add_field("firstLastPiecePrio", bool_str(self._first_last_piece_prio))

        if self._stop_condition is not None:
            form.add_field("stopCondition", self._stop_condition)

        if self._content_layout is not None:
            form.add_field("contentLayout", self._content_layout)

        return form

    @classmethod
    def with_client(cls, client: "APIClient") -> Self:
        """
        Return :class:`.AddFormBuilder` to build :class:`~aiohttp.FormData`
        used in :meth:`.TorrentsAPI.add`.

        :param client: :class:`.APIClient`.
        :return: :class:`.AddFormBuilder`.
        """

        return cls(
            client_version=client.client_version,
            api_version=client.api_version,
        )


def _convert_duration(
    delta: Union[timedelta, float],
    unit: TimeUnit,
) -> float:
    """
    Convert duration to float

    timedelta is converted to the unit or seconds if not specified.
    int/float is returned unchanged.
    """
    if isinstance(delta, timedelta):
        delta = unit.from_seconds(delta.total_seconds())

        if TYPE_CHECKING:
            assert isinstance(delta, (int, float))

    return delta


def _convert_path(path: StrPath) -> str:
    """Convert path-like objects to POSIX path str"""
    return os.fsdecode(path).replace("\\", "/")
