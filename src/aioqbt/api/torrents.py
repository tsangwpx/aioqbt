import dataclasses
import os
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
    RatioLimits,
    SeedingTimeLimits,
    ShareLimitAction,
    StopCondition,
    TorrentInfo,
    TorrentProperties,
    TorrentSSLParameters,
    Tracker,
    WebSeed,
)
from aioqbt.bittorrent import InfoHash, InfoHashes, InfoHashesOrAll, _info_hash_str
from aioqbt.chrono import Minutes, TimeUnit
from aioqbt.client import APIClient, APIGroup, since, virtual
from aioqbt.typing import StrPath
from aioqbt.version import APIVersion, ClientVersion

__all__ = (
    "AddFormBuilder",
    "TorrentsAPI",
)


def _check_iterable_except_str(param: str, value: Iterable[Any]) -> None:
    """Explicitly reject ``str`` as ``Iterable[str]``"""
    if isinstance(value, str):  # pragma: no cover
        raise ValueError(f"{param!r} refused str as iterable")


def _adapt_info_filter(
    filter: str,
    api_version: Optional[Tuple[int, int, int]],
) -> str:
    """
    Normalize info filter across qBittorrent versions
    and issue warnings about it
    """

    # Before API v2.11.0,
    # RUNNING was called RESUMED
    # STOPPED was called PAUSED

    msg: Optional[str] = None

    if APIVersion.compare(api_version, (2, 11, 0)) >= 0:
        if filter == InfoFilter.RESUMED:
            msg = "Please migrate RESUMED to RUNNING in qBittorrent v5"
            filter = InfoFilter.RUNNING
        elif filter == InfoFilter.PAUSED:
            msg = "Please migrate PAUSED to STOPPED in qBittorrent v5"
            filter = InfoFilter.STOPPED
    else:
        if filter == InfoFilter.RUNNING:
            filter = InfoFilter.RESUMED
        if filter == InfoFilter.STOPPED:
            filter = InfoFilter.PAUSED

    if msg is not None:
        import warnings

        warnings.warn(msg, DeprecationWarning, stacklevel=3)

    return filter


class TorrentsAPI(APIGroup):
    """
    API methods under ``torrents``.
    """

    async def count(self) -> int:
        """
        Get the number of torrents
        """
        # new in v4.6.1
        result = await self._request_text(
            "GET",
            "torrents/count",
        )
        return int(result)

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

        if filter is not None:
            filter = _adapt_info_filter(filter, self._client().api_version)
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
            # API 2.8.3
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
            props.hash = _info_hash_str(hash)

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
            # API 2.8.2
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
        return await self._request_json(  # type: ignore[no-any-return]
            "GET",
            "torrents/pieceStates",
            params=ParamDict.with_hash(hash),
        )

    async def piece_hashes(self, hash: InfoHash) -> List[str]:
        """
        A list of piece hashes in a torrent.
        """

        return await self._request_json(  # type: ignore[no-any-return]
            "GET",
            "torrents/pieceHashes",
            params=ParamDict.with_hash(hash),
        )

    async def stop(self, hashes: InfoHashesOrAll) -> None:
        """
        Stop torrents.

        Torrents can be specified by their info hashes.
        Passing ``all`` stops all torrents.

        """

        client = self._client()

        if APIVersion.compare(client.api_version, (2, 11, 0)) >= 0:
            endpoint = "torrents/stop"
        else:
            endpoint = "torrents/pause"

        await self._request_text(
            "POST",
            endpoint,
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def pause(self, hashes: InfoHashesOrAll) -> None:
        """Alias of :meth:`.stop`."""
        return await self.stop(hashes)

    async def start(self, hashes: InfoHashesOrAll) -> None:
        """
        Start torrents.

        Torrents can be specified by their info hashes.
        Passing ``all`` starts all torrents.

        """

        client = self._client()

        if APIVersion.compare(client.api_version, (2, 11, 0)) >= 0:
            endpoint = "torrents/start"
        else:
            endpoint = "torrents/resume"

        await self._request_text(
            "POST",
            endpoint,
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def resume(self, hashes: InfoHashesOrAll) -> None:
        """Alias of :meth:`.start`."""
        return await self.start(hashes)

    async def delete(self, hashes: InfoHashesOrAll, delete_files: bool) -> None:
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

    async def recheck(self, hashes: InfoHashesOrAll) -> None:
        """Recheck torrents."""

        await self._request_text(
            "POST",
            "torrents/recheck",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def reannounce(self, hashes: InfoHashesOrAll) -> None:
        """Reannounce torrents."""

        # since API v2.0.2

        await self._request_text(
            "POST",
            "torrents/reannounce",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def add(self, form: aiohttp.FormData) -> None:
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

    async def add_trackers(self, hash: InfoHash, trackers: Iterable[str]) -> None:
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
    ) -> None:
        data = ParamDict.with_hash(hash)
        data.required_str("origUrl", orig_url)
        data.required_str("newUrl", new_url)

        await self._request_text(
            "POST",
            "torrents/editTracker",
            data=data,
        )

    async def remove_trackers(self, hash: InfoHash, urls: Iterable[str]) -> None:
        _check_iterable_except_str("urls", urls)

        # Since API v2.2.0
        data = ParamDict.with_hash(hash)
        data.required_list("urls", urls, "|")

        await self._request_text(
            "POST",
            "torrents/removeTrackers",
            data=data,
        )

    async def add_peers(self, hashes: InfoHashes, peers: Iterable[str]) -> None:
        _check_iterable_except_str("peers", peers)

        data = ParamDict.with_hashes(hashes)
        data.required_list("peers", peers, "|")

        await self._request_text(
            "POST",
            "torrents/addPeers",
            data=data,
        )

    async def top_prio(self, hashes: InfoHashesOrAll) -> None:
        await self._request_text(
            "POST",
            "torrents/topPrio",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def bottom_prio(self, hashes: InfoHashesOrAll) -> None:
        await self._request_text(
            "POST",
            "torrents/bottomPrio",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def increase_prio(self, hashes: InfoHashesOrAll) -> None:
        await self._request_text(
            "POST",
            "torrents/increasePrio",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def decrease_prio(self, hashes: InfoHashesOrAll) -> None:
        await self._request_text(
            "POST",
            "torrents/decreasePrio",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def file_prio(self, hash: InfoHash, id: Iterable[int], priority: int) -> None:
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
        return result  # type: ignore[no-any-return]

    async def set_download_limit(self, hashes: InfoHashesOrAll, limit: int) -> None:
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
        ratio_limit: Union[float, RatioLimits],
        seeding_time_limit: Union[timedelta, int, SeedingTimeLimits],
        inactive_seeding_time_limit: Union[timedelta, int, SeedingTimeLimits, None] = None,
    ) -> None:
        """
        Set share limits for torrents.

        :param hashes: A list of info hashes or ``all`` for all torrents.
        :param ratio_limit: A number or :attr:`.RatioLimits.UNSET`.
        :param seeding_time_limit: :class:`~datetime.timedelta`, or
                :class:`.SeedingTimeLimits` constants.
        :param inactive_seeding_time_limit: :class:`~datetime.timedelta`, or
                :class:`.InactiveSeedingTimeLimits` constants.
                Required since qBittorrent v4.6.0 (API 2.9.2).
        """
        # since API v2.0.1
        client = self._client()

        data = ParamDict.with_hashes_or_all(hashes)
        data.required_float("ratioLimit", ratio_limit)
        data.required_duration("seedingTimeLimit", seeding_time_limit, TimeUnit.MINUTES)

        if inactive_seeding_time_limit is not None:
            data.required_duration(
                "inactiveSeedingTimeLimit", inactive_seeding_time_limit, TimeUnit.MINUTES
            )

        try:
            await client.request_text(
                "POST",
                "torrents/setShareLimits",
                data=data,
            )
        except exc.BadRequestError as ex:
            if (
                inactive_seeding_time_limit is None
                and APIVersion.compare(client.api_version, (2, 9, 2)) >= 0
            ):
                note = "Argument 'inactive_seeding_time_limit' is required since qBittorrent 4.6.0"
                exc._add_note(ex, note, logger=client._logger)

            raise

    async def upload_limit(self, hashes: InfoHashesOrAll) -> Dict[str, int]:
        """
        Get torrent upload limits.

        The result is a dict mapping info hash to upload speed limit
        in bytes/second.

        :param hashes: A list of info hashes or ``all`` for all torrents.
        """
        params = ParamDict.with_hashes_or_all(hashes)

        return await self._request_json(  # type: ignore[no-any-return]
            "GET",
            "torrents/uploadLimit",
            params=params,
        )

    async def set_upload_limit(self, hashes: InfoHashesOrAll, limit: int) -> None:
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
    ) -> None:
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
    ) -> None:
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
    ) -> None:
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

    async def rename(self, hash: InfoHash, name: str) -> None:
        """Rename a torrent."""
        data = ParamDict.with_hash(hash)
        data.required_str("name", name)

        await self._request_text(
            "POST",
            "torrents/rename",
            data=data,
        )

    async def set_category(self, hashes: InfoHashesOrAll, category: str) -> None:
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

    async def create_category(self, category: str, save_path: StrPath) -> None:
        """Create category."""
        data = ParamDict()
        data.required_str("category", category)
        data.required_path("savePath", save_path)

        await self._request_text(
            "POST",
            "torrents/createCategory",
            data=data,
        )

    async def edit_category(self, category: str, save_path: StrPath) -> None:
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

    async def remove_categories(self, categories: Iterable[str]) -> None:
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
    async def add_tags(self, hashes: InfoHashesOrAll, tags: Iterable[str]) -> None:
        _check_iterable_except_str("tags", tags)

        data = ParamDict.with_hashes_or_all(hashes)
        data.required_list("tags", tags, ",")

        await self._request_text(
            "POST",
            "torrents/addTags",
            data=data,
        )

    @since((2, 3, 0))
    async def remove_tags(self, hashes: InfoHashesOrAll, tags: Iterable[str]) -> None:
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
        return await self._request_json(  # type: ignore[no-any-return]
            "GET",
            "torrents/tags",
        )

    @since((2, 3, 0))
    async def create_tags(self, tags: Iterable[str]) -> None:
        _check_iterable_except_str("tags", tags)

        data = ParamDict()
        data.required_list("tags", tags, ",")
        await self._request_text(
            "POST",
            "torrents/createTags",
            data=data,
        )

    @since((2, 3, 0))
    async def delete_tags(self, tags: Iterable[str]) -> None:
        _check_iterable_except_str("tags", tags)

        data = ParamDict()
        data.required_list("tags", tags, ",")
        await self._request_text(
            "POST",
            "torrents/deleteTags",
            data=data,
        )

    async def set_auto_management(self, hashes: InfoHashesOrAll, enable: bool) -> None:
        data = ParamDict.with_hashes_or_all(hashes)
        data.optional_bool("enable", enable)

        await self._request_text(
            "POST",
            "torrents/setAutoManagement",
            data=data,
        )

    async def toggle_sequential_download(self, hashes: InfoHashesOrAll) -> None:
        """Flip ``seq_dl`` values for torrents."""
        data = ParamDict.with_hashes_or_all(hashes)

        await self._request_text(
            "POST",
            "torrents/toggleSequentialDownload",
            data=data,
        )

    @virtual
    async def set_sequential_download(self, hashes: InfoHashesOrAll, value: bool) -> None:
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

    async def toggle_first_last_piece_prio(self, hashes: InfoHashesOrAll) -> None:
        """Flip ``f_l_piece_prio`` values for torrents."""
        await self._request_text(
            "POST",
            "torrents/toggleFirstLastPiecePrio",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    @virtual
    async def set_first_last_piece_prio(self, hashes: InfoHashesOrAll, value: bool) -> None:
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

    async def set_force_start(self, hashes: InfoHashesOrAll, force: bool) -> None:
        """Set ``force_start`` flags for torrents."""
        data = ParamDict.with_hashes_or_all(hashes)
        data.required_bool("value", force)

        await self._request_text(
            "POST",
            "torrents/setForceStart",
            data=data,
        )

    async def set_super_seeding(self, hashes: InfoHashesOrAll, value: bool) -> None:
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
    async def rename_file(self, hash: InfoHash, id: int, name: str) -> None:
        """available until client 4.3.3"""

    @overload
    async def rename_file(self, hash: InfoHash, old_path: str, new_path: str) -> None:
        """available since client 4.3.3 or API 2.7.0"""

    async def rename_file(self, hash: InfoHash, *args: Any, **kwargs: Any) -> None:
        """
        Rename a file in torrent.

        On qBittorrent v4.3.3 or later, the signature is ``rename_file(hash, old_path, new_path)``.

        Below qBittorrent v4.3.3, use ``rename_file(hash, id, name)``, where ``id`` is
        the file index from :meth:`~.TorrentsAPI.files`.

        Available since qBittorrent v4.2.1 (API 2.4.0).

        Signature changed in v4.3.3 (API 2.7.0).

        See also: https://github.com/qbittorrent/qBittorrent/pull/13995

        """
        # API 2.4.0

        client = self._client()
        legacy = APIVersion.compare(client.api_version, (2, 7, 0)) < 0
        nargs = len(args)

        if nargs > 2:
            raise TypeError("Too many arguments")
        if nargs == 2:
            pass
        elif nargs == 1:
            # Missing one argument
            key = "name" if isinstance(args[0], int) else "new_path"
            try:
                args += (kwargs.pop(key),)
            except KeyError:
                raise TypeError(f"Missing argument {key!r}") from None
        else:
            try:
                if "old_path" in kwargs:
                    args = (kwargs.pop("old_path"), kwargs.pop("new_path"))
                elif "id" in kwargs:
                    args = (kwargs.pop("id"), kwargs.pop("name"))
                else:
                    raise KeyError("id" if legacy else "old_path")
            except KeyError as ex:
                raise TypeError(f"Missing argument {ex.args[0]!r}") from None

        if kwargs:
            raise TypeError(f"Extra keyword arguments: {kwargs.keys()!r}")

        arg, arg2 = args

        data = ParamDict.with_hash(hash)
        if isinstance(arg, str):
            data.required_str("oldPath", arg)
            data.required_str("newPath", arg2)
        elif isinstance(arg, int):
            data.required_int("id", arg)
            data.required_str("name", arg2)
        else:
            raise TypeError(f"Bad call signature: ({type(hash)!r}, {type(arg)!r}, {type(arg2)!r})")

        try:
            await self._request_text(
                "POST",
                "torrents/renameFile",
                data=data,
            )
        except exc.BadRequestError as ex:
            if APIVersion.compare(self._client().api_version, (2, 4, 0)) >= 0:
                note = (
                    "From qBittorrent 4.2.1, rename_file(hash, id, name) was changed"
                    " to rename_file(hash, old_path, new_path)."
                    " BadRequestError may raise if rename_file() was called"
                    " with inappropriate arguments."
                )
                exc._add_note(ex, note, logger=self._client()._logger)

            raise

    @since((2, 8, 0))
    async def rename_folder(self, hash: InfoHash, old_path: str, new_path: str) -> None:
        """Rename a folder."""
        # API 2.8.0

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

    @since((2, 10, 4))
    async def ssl_parameters(self, hash: InfoHash) -> TorrentSSLParameters:
        """
        Get SSL parameters
        """

        params = ParamDict.with_hash(hash)

        return await self._request_mapped_object(
            TorrentSSLParameters,
            "GET",
            "torrents/SSLParameters",
            params=params,
        )

    @since((2, 10, 4))
    async def set_ssl_parameters(
        self,
        hash: InfoHash,
        ssl_certificate: str,
        ssl_private_key: str,
        ssl_dh_params: str,
    ) -> None:
        """
        Set SSL parameters
        """

        data = ParamDict.with_hash(hash)
        data.required_str("ssl_certificate", ssl_certificate)
        data.required_str("ssl_private_key", ssl_private_key)
        data.required_str("ssl_dh_params", ssl_dh_params)

        await self._request_text(
            "POST",
            "torrents/setSSLParameters",
            data=data,
        )


@dataclasses.dataclass
class AddFormBuilder:
    """
    Build :class:`aiohttp.FormData` used in :meth:`.TorrentsAPI.add`.

    AddFormBuilder is designed in fluent interface.
    Most of its methods return a modified copy of the builder.

    Here is an example to illustrate::

        await client.torrent.add(
            # Create a builder with a particular client
            AddFormBuilder.with_client(client)

            # Set torrent category to "linux"
            .category("linux")

            # Set ratio limit to 10
            .ratio_limit(10)

            # Add a torrent by its info hash (debian-11.7.0-amd64-netinst.iso)
            .include_url("6f84758b0ddd8dc05840bf932a77935d8b5b8b93")

            # Add a torrent by URL/magnet link (debian-11.6.0-amd64-netinst.iso)
            .include_url("magnet:?xt=urn:btih:6d4795dee70aeb88e03e5336ca7c9fcf0a1e206d")

            # Upload a torrent with its bytes data and name
            .include_url(file_bytes, "debian-12.0.0-amd64-netinst.iso")

            # Generate FormData object
            .build()
        )

    See also :APIWiki:`torrents/add <#add-new-torrent>`.

    """

    client_version: Optional[ClientVersion] = None
    api_version: Optional[APIVersion] = None

    _urls: List[str] = dataclasses.field(default_factory=list)
    _files: List[Tuple[bytes, str]] = dataclasses.field(default_factory=list)

    _savepath: Optional[str] = None
    _download_path: Optional[str] = None
    _use_download_path: Optional[bool] = None
    _cookie: Optional[str] = None
    _category: Optional[str] = None
    _tags: Optional[str] = None
    _skip_checking: Optional[bool] = None
    _paused: Optional[bool] = None
    _stopped: Optional[bool] = None
    _root_folder: Optional[bool] = None
    _rename: Optional[str] = None
    _up_limit: Optional[int] = None
    _dl_limit: Optional[int] = None
    _ratio_limit: Optional[float] = None
    _seeding_time_limit: Optional[int] = None
    _inactive_seeding_time_limit: Optional[int] = None
    _auto_tmm: Optional[bool] = None
    _sequential_download: Optional[bool] = None
    _first_last_piece_prio: Optional[bool] = None
    _add_to_top_of_queue: Optional[bool] = None
    _stop_condition: Optional[str] = None
    _content_layout: Optional[str] = None
    _share_limit_action: Optional[int] = None

    _ssl_certificate: Optional[str] = None
    _ssl_private_key: Optional[str] = None
    _ssl_dh_params: Optional[str] = None

    def __deepcopy__(self, memodict: Optional[Dict[int, Any]] = None) -> Self:
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
    def savepath(self, savepath: Optional[StrPath]) -> Self:
        """Set ``savepath`` value."""
        self._savepath = None if savepath is None else _convert_path(savepath)
        return self

    @copy_self
    def download_path(self, download_path: Optional[StrPath]) -> Self:
        """
        Set ``downloadPath`` value.

        Also use :meth:`use_download_path(True) <.use_download_path>` to enable download path.
        """
        # API v2.8.4
        self._download_path = None if download_path is None else _convert_path(download_path)
        return self

    @copy_self
    def use_download_path(self, use_download_path: Optional[bool]) -> Self:
        """
        Set ``useDownloadPath`` value.
        """
        # API v2.8.4
        self._use_download_path = use_download_path
        return self

    @copy_self
    def cookie(self, cookie: Optional[str]) -> Self:
        """Set ``cookie`` value."""
        self._cookie = cookie
        return self

    @copy_self
    def category(self, category: Optional[str]) -> Self:
        """Set ``category`` value."""
        self._category = category
        return self

    @copy_self
    def tags(self, tags: Optional[Iterable[str]]) -> Self:
        """
        Associate torrents being added with tags.

        Available since API v2.6.2.

        :param tags: list of tags.
        """
        if tags is None:
            self._tags = None
            return self

        # API 2.6.2
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
    def skip_checking(self, skip_checking: Optional[bool]) -> Self:
        """Set ``skip_checking`` value."""
        self._skip_checking = skip_checking
        return self

    @copy_self
    def paused(self, paused: Optional[bool]) -> Self:
        """Set ``paused`` value."""

        if APIVersion.compare(self.api_version, (2, 11, 0)) >= 0:
            import warnings

            warnings.warn(
                "use stopped() instead of paused() in API v2.11.0 or later",
                DeprecationWarning,
                stacklevel=3,
            )
            self._stopped = paused

        self._paused = paused
        return self

    @copy_self
    def stopped(self, stopped: Optional[bool]) -> Self:
        """Set ``stopped`` value."""

        if APIVersion.compare(self.api_version, (2, 11, 0)) < 0:
            # also set the "paused" field but do not issue warnings
            # older client would ignore the "stopped" field and use the "paused" field.
            self._paused = stopped

        self._stopped = stopped
        return self

    @copy_self
    def root_folder(self, root_folder: Optional[bool]) -> Self:
        """
        Set ``root_folder`` value.

        Removed on qBittorrent v4.3.2 and later. Use :meth:`.content_layout` instead.
        """
        self._root_folder = root_folder
        return self

    @copy_self
    def rename(self, rename: Optional[str]) -> Self:
        """Set ``rename`` value, which is the new torrent name."""
        self._rename = rename
        return self

    @copy_self
    def up_limit(self, up_limit: Optional[int]) -> Self:
        """Set ``upLimit`` in bytes/s"""
        self._up_limit = up_limit
        return self

    @copy_self
    def dl_limit(self, dl_limit: Optional[int]) -> Self:
        """Set ``dlLimit`` in bytes/s"""
        self._dl_limit = dl_limit
        return self

    @copy_self
    @since((2, 8, 1))
    def ratio_limit(self, ratio_limit: Union[float, RatioLimits, None]) -> Self:
        """Set ``ratioLimit`` value."""
        # API 2.8.1
        self._ratio_limit = None if ratio_limit is None else float(ratio_limit)
        return self

    @copy_self
    @since((2, 8, 1))
    def seeding_time_limit(
        self,
        seeding_time_limit: Union[timedelta, Minutes, SeedingTimeLimits, None],
    ) -> Self:
        """Set ``seedingTimeLimit`` value."""
        # API 2.8.1
        if seeding_time_limit is None:
            self._seeding_time_limit = None
        else:
            self._seeding_time_limit = int(_convert_duration(seeding_time_limit, TimeUnit.MINUTES))
        return self

    @copy_self
    def inactive_seeding_time_limit(
        self,
        inactive_seeding_time_limit: Union[timedelta, Minutes, SeedingTimeLimits, None],
    ) -> Self:
        """Set ``inactiveSeedingTimeLimit`` value."""
        # API 2.9.2
        if inactive_seeding_time_limit is None:
            self._inactive_seeding_time_limit = None
        else:
            self._inactive_seeding_time_limit = int(
                _convert_duration(inactive_seeding_time_limit, TimeUnit.MINUTES)
            )
        return self

    @copy_self
    def auto_tmm(self, auto_tmm: Optional[bool]) -> Self:
        """Set ``autoTMM`` value."""
        self._auto_tmm = auto_tmm
        return self

    @copy_self
    def sequential_download(self, sequential_download: Optional[bool]) -> Self:
        """Set ``sequentialDownload`` value."""
        self._sequential_download = sequential_download
        return self

    @copy_self
    def first_last_piece_prio(self, first_last_piece_prio: Optional[bool]) -> Self:
        """Set ``firstLastPiecePrio`` value."""
        self._first_last_piece_prio = first_last_piece_prio
        return self

    @copy_self
    def add_to_top_of_queue(self, add_to_top_of_queue: Optional[bool]) -> Self:
        """Set ``addToTopOfQueue`` value"""
        # found in v4.6.0, API 2.8.19
        self._add_to_top_of_queue = add_to_top_of_queue
        return self

    @copy_self
    def stop_condition(self, stop_condition: Optional[StopCondition]) -> Self:
        """Set ``stopCondition`` value."""
        # API v2.8.15
        self._stop_condition = None if stop_condition is None else str(stop_condition)
        return self

    @copy_self
    def content_layout(self, content_layout: Optional[ContentLayout]) -> Self:
        """Set ``contentLayout`` value."""
        # API v2.7.0
        self._content_layout = None if content_layout is None else str(content_layout)
        return self

    @copy_self
    def share_limit_action(self, share_limit_action: Union[int, ShareLimitAction, None]) -> Self:
        """Set ``shareLimitAction`` value"""
        # API v2.11.0
        if share_limit_action is not None:
            share_limit_action = int(share_limit_action)

        self._share_limit_action = share_limit_action
        return self

    @copy_self
    def ssl_certificate(self, ssl_certificate: Optional[str]) -> Self:
        """
        Set ``ssl_certificate`` value.

        The certificate is stored in PEM format.
        """
        self._ssl_certificate = ssl_certificate
        return self

    @copy_self
    def ssl_private_key(self, ssl_private_key: Optional[str]) -> Self:
        """
        Set ``ssl_private_key`` value.

        The private key is stored in PEM format.
        RSA and EC keys are supported.
        """
        self._ssl_private_key = ssl_private_key
        return self

    @copy_self
    def ssl_dh_params(self, ssl_dh_params: Optional[str]) -> Self:
        """
        Set ``ssl_dh_params`` value.

        The Diffie–Hellman key exchange parameters is stored in PEM format.
        """
        self._ssl_dh_params = ssl_dh_params
        return self

    def build(self) -> aiohttp.FormData:
        """
        Build :class:`~aiohttp.FormData`.
        """

        def bool_str(b: bool) -> str:
            """boolean to lowercase string"""
            return "true" if b else "false"

        form = aiohttp.FormData()

        if self._urls:
            content_type = None
            if APIVersion.compare(self.api_version, (2, 6, 0)) < 0:
                # Force multipart/form-data with content_type
                # Workaround issue in qBittorrent 4.1 (4.2?)
                # See https://github.com/qbittorrent/qBittorrent/pull/10458
                content_type = "text/plain"

            form.add_field("urls", "\n".join(self._urls), content_type=content_type)

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

        if self._tags is not None:
            form.add_field("tags", self._tags)

        if self._skip_checking is not None:
            form.add_field("skip_checking", bool_str(self._skip_checking))

        if self._paused is not None:
            form.add_field("paused", bool_str(self._paused))

        if self._stopped is not None:
            form.add_field("stopped", bool_str(self._stopped))

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

        if self._inactive_seeding_time_limit is not None:
            form.add_field("inactiveSeedingTimeLimit", str(self._inactive_seeding_time_limit))

        if self._auto_tmm is not None:
            form.add_field("autoTMM", bool_str(self._auto_tmm))

        if self._sequential_download is not None:
            form.add_field("sequentialDownload", bool_str(self._sequential_download))

        if self._add_to_top_of_queue is not None:
            form.add_field("addToTopOfQueue", bool_str(self._add_to_top_of_queue))

        if self._first_last_piece_prio is not None:
            form.add_field("firstLastPiecePrio", bool_str(self._first_last_piece_prio))

        if self._stop_condition is not None:
            form.add_field("stopCondition", self._stop_condition)

        if self._content_layout is not None:
            form.add_field("contentLayout", self._content_layout)

        if self._share_limit_action is not None:
            form.add_field("shareLimitAction", str(self._share_limit_action))

        if self._ssl_certificate is not None:
            form.add_field("ssl_certificate", self._ssl_certificate)

        if self._ssl_private_key is not None:
            form.add_field("ssl_private_key", self._ssl_private_key)

        if self._ssl_dh_params is not None:
            form.add_field("ssl_dh_params", self._ssl_dh_params)

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
