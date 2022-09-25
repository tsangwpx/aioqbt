import dataclasses
import os
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Tuple, Union, overload

import aiohttp

from aioqbt import exc
from aioqbt._decorator import copy_self
from aioqbt._paramdict import ParamDict
from aioqbt.api.types import (
    Category,
    FileEntry,
    InfoFilter,
    RatioLimitTypes,
    SeedingTimeLimitTypes,
    TorrentInfo,
    TorrentProperties,
    Tracker,
    WebSeed,
)
from aioqbt.bittorrent import InfoHash, InfoHashes, InfoHashesOrAll, get_info_hash
from aioqbt.chrono import TimeUnit
from aioqbt.client import APIClient, APIGroup, since, virtual
from aioqbt.version import APIVersion, ClientVersion, param_version_check, version_check

__all__ = (
    "AddFormBuilder",
    "TorrentsAPI",
)

_PathLike = Union[str, os.PathLike[str]]


def _check_iterable_except_str(param: str, value: Iterable[Any]):
    """Explicitly reject ``str`` as ``Iterable[str]``"""
    if isinstance(value, str):  # pragma: no cover
        raise ValueError(f"{param!r} excepts an iterable except str")


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
        Get a list of :class:`TorrentInfo`.

        There is :class:`.InfoFilter` enum to substitute ``str`` in ``filter``.
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
        props = await self._request_mapped_object(
            TorrentProperties,
            "GET",
            "torrents/properties",
            params=ParamDict.with_hash(hash),
        )
        props._hash = get_info_hash(hash)
        return props

    async def trackers(self, hash: InfoHash) -> List[Tracker]:
        # Tracker's status may be a string or int, API v2.2.0
        return await self._request_mapped_list(
            Tracker,
            "GET",
            "torrents/trackers",
            params=ParamDict.with_hash(hash),
        )

    async def webseeds(self, hash: InfoHash) -> List[WebSeed]:
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
        Return a list of piece states for a torrent.

        Use :class:`.PieceState` to compare states.
        """
        return await self._request_json(
            "GET",
            "torrents/pieceStates",
            params=ParamDict.with_hash(hash),
        )

    async def piece_hashes(self, hash: InfoHash) -> List[str]:
        return await self._request_json(
            "GET",
            "torrents/pieceHashes",
            params=ParamDict.with_hash(hash),
        )

    async def pause(self, hashes: InfoHashesOrAll):
        await self._request_text(
            "POST",
            "torrents/pause",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def resume(self, hashes: InfoHashesOrAll):
        await self._request_text(
            "POST",
            "torrents/resume",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def delete(self, hashes: InfoHashesOrAll, delete_files: bool):
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
        await self._request_text(
            "POST",
            "torrents/recheck",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def reannounce(self, hashes: InfoHashesOrAll):
        # since API v2.0.2

        await self._request_text(
            "POST",
            "torrents/reannounce",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    async def add(self, form: aiohttp.FormData):
        """
        Submit :class:`~aiohttp.FormData` to add torrents from bytes, hashes, and/or URLs.

        Forms can be built with :class:`.AddFormBuilder`.
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

        ``id`` are a list of file indices.
        Use :class:`.FilePriority` to specify ``priority``.
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
        params = ParamDict.with_hashes_or_all(hashes)
        result = await self._request_json(
            "GET",
            "torrents/downloadLimit",
            params=params,
        )
        return result

    async def set_download_limit(self, hashes: InfoHashesOrAll, limit: int):
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

        :param hashes: hash list or ``all``.
        :param ratio_limit: number or :attr:`.RatioLimits.UNSET`.
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
        params = ParamDict.with_hashes_or_all(hashes)

        return await self._request_json(
            "GET",
            "torrents/uploadLimit",
            params=params,
        )

    async def set_upload_limit(self, hashes: InfoHashesOrAll, limit: int):
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
        location: _PathLike,
    ):
        data = ParamDict.with_hashes_or_all(hashes)
        data.required_path("location", location)

        await self._request_text(
            "POST",
            "torrents/setLocation",
            data=data,
        )

    async def rename(self, hash: InfoHash, name: str):
        data = ParamDict.with_hash(hash)
        data.required_str("name", name)

        await self._request_text(
            "POST",
            "torrents/rename",
            data=data,
        )

    async def set_category(self, hashes: InfoHashesOrAll, category: str):
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
        Return a dict from name to :class:`.Category`.
        """
        return await self._request_mapped_dict(
            Category,
            "GET",
            "torrents/categories",
        )

    async def create_category(self, category: str, save_path: _PathLike):
        data = ParamDict()
        data.required_str("category", category)
        data.required_path("savePath", save_path)

        await self._request_text(
            "POST",
            "torrents/createCategory",
            data=data,
        )

    async def edit_category(self, category: str, save_path: _PathLike):
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

        This method is virtual that torrents in interest are filtered
        and flags are toggled in steps.
        """
        torrents = await self.info(hashes=hashes)
        targets = []

        for info in torrents:
            if info.seq_dl != value:
                targets.append(info.hash)

        if targets:
            await self.toggle_sequential_download(targets)

    async def toggle_first_last_piece_prio(self, hashes: InfoHashesOrAll):
        await self._request_text(
            "POST",
            "torrents/toggleFirstLastPiecePrio",
            data=ParamDict.with_hashes_or_all(hashes),
        )

    @virtual
    async def set_first_last_piece_prio(self, hashes: InfoHashesOrAll, value: bool):
        """
        Change ``f_l_piece_prio`` for torrents.

        This method is virtual that torrents in interest are filtered
        and flags are toggled in steps.
        """
        torrents = await self.info(hashes=hashes)
        targets = []

        for info in torrents:
            if info.f_l_piece_prio != value:
                targets.append(info.hash)

        if targets:
            await self.toggle_first_last_piece_prio(targets)

    async def set_force_start(self, hashes: InfoHashesOrAll, force: bool):
        data = ParamDict.with_hashes_or_all(hashes)
        data.required_bool("value", force)

        await self._request_text(
            "POST",
            "torrents/setForceStart",
            data=data,
        )

    async def set_super_seeding(self, hashes: InfoHashesOrAll, value: bool):
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
        """available since client 4.3.3 or API 2.8.0"""

    @since((2, 4, 0))
    async def rename_file(self, hash, arg, arg2):
        """
        Rename file in torrent.

        The method is available since API v2.4.0 and
        its signature depends on client and API versions.

        Until API v2.8.0: ``rename_file(hash, id, name)``,
        where ``id`` is item index in :meth:`.files`.

        After API v2.8.0: ``rename_file(hash, old_path, new_path)``.

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
        version_check(self._client().api_version, (2, 8, 0))

        data = ParamDict.with_hash(hash)
        data.required_path("oldPath", old_path)
        data.required_path("newPath", new_path)

        await self._request_text(
            "POST",
            "torrents/renameFolder",
            data=data,
        )


@dataclass
class AddFormBuilder:
    """
    Helper to build :class:`~aiohttp.FormData` in :meth:`~TorrentsAPI.add`.

    :class:`.AddFormBuilder` is an immutable object.
    Builder methods return a modified copy instead of updating itself.
    """

    client_version: Optional[ClientVersion] = None
    api_version: Optional[APIVersion] = None

    _urls: List[str] = field(default_factory=list)
    _files: List[Tuple[bytes, str]] = field(default_factory=list)

    _savepath: Optional[str] = None
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

    def __deepcopy__(self, memodict=None):
        return dataclasses.replace(
            self,
            _urls=list(self._urls),
            _files=list(self._files),
        )

    __copy__ = __deepcopy__

    @copy_self
    def include_url(self, url: str):
        """
        Add a URL, magnet link, or SHA1 hash.
        """

        self._urls.append(url)
        return self

    @copy_self
    def include_file(self, data: bytes, filename: Optional[str] = None):
        """
        Add a torrent file.
        """

        if filename is None:
            filename = f"{len(self._files) + 1:d}.torrent"

        self._files.append((bytes(data), filename))
        return self

    def add_url(self, url: str):
        # deprecated, use include_url() instead
        return self.include_url(url)  # pragma: no cover

    def add_torrent(self, filename: str, data: bytes):
        # deprecated, use include_file() instead
        return self.include_file(data, filename)  # pragma: no cover

    @copy_self
    def savepath(self, savepath: _PathLike):
        """Set ``savepath``"""
        self._savepath = _convert_path(savepath)
        return self

    @copy_self
    def cookie(self, cookie: str):
        """Set ``cookie``"""
        self._cookie = cookie
        return self

    @copy_self
    def category(self, category: str):
        """Set ``category``"""
        self._category = category
        return self

    @copy_self
    def tags(self, tags: Iterable[str]):
        """
        Set ``tags``

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
    def skip_checking(self, skip_checking: bool):
        """Set ``skip_checking``"""
        self._skip_checking = skip_checking
        return self

    @copy_self
    def paused(self, paused: bool):
        """Set ``paused``"""
        self._paused = paused
        return self

    @copy_self
    def root_folder(self, root_folder: bool):
        """Set ``root_folder``"""
        self._root_folder = root_folder
        return self

    @copy_self
    def rename(self, rename: str):
        """Set ``rename``"""
        self._rename = rename
        return self

    @copy_self
    def up_limit(self, up_limit: int):
        """Set ``upLimit`` in bytes/s"""
        self._up_limit = up_limit
        return self

    @copy_self
    def dl_limit(self, dl_limit: int):
        """Set ``dlLimit`` in bytes/s"""
        self._dl_limit = dl_limit
        return self

    @copy_self
    @since((2, 8, 1))
    def ratio_limit(self, ratio_limit: RatioLimitTypes):
        """Set ``ratioLimit``"""
        version_check(self.api_version, (2, 8, 1))
        self._ratio_limit = float(ratio_limit)
        return self

    @copy_self
    @since((2, 8, 1))
    def seeding_time_limit(self, seeding_time_limit: SeedingTimeLimitTypes):
        """Set ``seedingTimeLimit``"""
        version_check(self.api_version, (2, 8, 1))
        self._seeding_time_limit = int(_convert_duration(seeding_time_limit, TimeUnit.MINUTES))
        return self

    @copy_self
    def auto_tmm(self, auto_tmm: bool):
        """Set ``autoTMM``"""
        self._auto_tmm = auto_tmm
        return self

    @copy_self
    def sequential_download(self, sequential_download: bool):
        """Set ``sequentialDownload``"""
        self._sequential_download = sequential_download
        return self

    @copy_self
    def first_last_piece_prio(self, first_last_piece_prio: bool):
        """Set firstLastPiecePrio"""
        self._first_last_piece_prio = first_last_piece_prio
        return self

    def build(self) -> aiohttp.FormData:
        """
        Build :class:`aiohttp.FormData`.
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

        return form

    @classmethod
    def with_client(cls, client: "APIClient"):
        """
        Return :class:`.AddFormBuilder` instance to :meth:`~.AddFormBuilder.build`
        :class:`~aiohttp.FormData` used in :meth:`.TorrentsAPI.add`.

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


def _convert_path(path: _PathLike) -> str:
    """Convert path-like objects to POSIX path str"""
    return os.fsdecode(path).replace("\\", "/")
