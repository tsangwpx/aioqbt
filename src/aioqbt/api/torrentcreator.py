from typing import List, Optional

from typing_extensions import Literal

from aioqbt._paramdict import ParamDict
from aioqbt.api.types import TorrentCreationAddResult, TorrentCreationTaskStatus
from aioqbt.client import APIGroup

__all__ = ("TorrentCreatorAPI",)


class TorrentCreatorAPI(APIGroup):
    """
    API methods under ``torrentcreator``.
    """

    async def add_task(
        self,
        *,
        source_path: str,
        private: Optional[bool] = None,
        format: Literal["v1", "v2", None] = None,
        optimize_alignment: Optional[bool] = None,
        padded_file_size_limit: Optional[int] = None,
        piece_size: Optional[int] = None,
        torrent_file_path: Optional[str] = None,
        comment: Optional[str] = None,
        source: Optional[str] = None,
        trackers: Optional[List[str]] = None,
        url_seeds: Optional[List[str]] = None,
        start_seeding: Optional[bool] = None,
    ) -> TorrentCreationAddResult:
        """
        Add torrent creation task.

        The result is a dict consisting of a task id.
        """
        data = ParamDict()
        data.required_str("sourcePath", source_path)
        data.optional_bool("private", private)
        data.optional_str("format", format)
        data.optional_bool("optimizeAlignment", optimize_alignment)
        data.optional_int("paddedFileSizeLimit", padded_file_size_limit)
        data.optional_int("pieceSize", piece_size)
        data.optional_str("torrentFilePath", torrent_file_path)
        data.optional_str("comment", comment)
        data.optional_str("source", source)
        data.optional_list("trackers", trackers, "|")
        data.optional_list("urlSeeds", url_seeds, "|")
        data.optional_bool("startSeeding", start_seeding)

        # transmit in www-form-urlencoded
        return await self._request_json(  # type: ignore[no-any-return]
            "POST",
            "torrentcreator/addTask",
            data=data,
        )

    async def status(self, task_id: Optional[str] = None) -> List[TorrentCreationTaskStatus]:
        """
        Return torrent creation task status(es).

        The result could be specified by `task_id` or all tasks would be returned.

        :raises ~exc.NotFoundError: if the task is specified but not found.
        """

        params = ParamDict()
        params.optional_str("taskID", task_id)

        return await self._client().request_json(  # type: ignore[no-any-return]
            "GET",
            "torrentcreator/status",
            params=params,
        )

    async def torrent_file(self, task_id: str) -> bytes:
        """
        Get the torrent file after creation.

        :raises ~exc.NotFoundError: if the task is not found.
        :raises ~exc.Conflict: if the task is either still on going or failed.
        """

        params = ParamDict()
        params.required_str("taskID", task_id)

        resp = await self._client().request(
            "GET",
            "torrentcreator/torrentFile",
            params=params,
        )

        async with resp:
            return await resp.read()

    async def delete_task(self, task_id: str) -> None:
        """
        Delete a task.

        :raises ~exc.NotFoundError: if the task is not found.
        """
        data = ParamDict()
        data.required_str("taskID", task_id)

        await self._request_text(
            "POST",
            "torrentcreator/delete",
            data=data,
        )
