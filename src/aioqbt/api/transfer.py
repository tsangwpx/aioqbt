from typing import Iterable, Tuple

from aioqbt._paramdict import ParamDict
from aioqbt.api.types import TransferInfo
from aioqbt.client import APIGroup
from aioqbt.version import APIVersion

__all__ = ("TransferAPI",)


def _check_1024(name: str, num: int):
    """num must be a multiple of 1024"""
    if num % 1024 != 0:
        raise ValueError(f"{name!r} must be a multiple of 1024")


class TransferAPI(APIGroup):
    """
    API methods under ``transfer``.
    """

    async def info(self) -> TransferInfo:
        return await self._request_mapped_object(
            TransferInfo,
            "GET",
            "transfer/info",
        )

    async def speed_limits_mode(self) -> int:
        # the response is a text of either "0" or "1"
        res = await self._request_text(
            "GET",
            "transfer/speedLimitsMode",
        )
        return int(res)

    async def toggle_speed_limits_mode(self):
        await self._request_text(
            "POST",
            "transfer/toggleSpeedLimitsMode",
        )

    async def set_speed_limits_mode(self, mode: int):
        """
        Change ``speed_limits_mode``.

        If API version is less than v2.8.14, a polyfill is used to set the mode.
        """

        if APIVersion.compare(self._client().api_version, (2, 8, 14)) < 0:
            await self._set_speed_limits_mode_polyfill(mode)
            return

        # since API v2.8.14
        data = ParamDict()
        data.required_int("mode", mode)

        await self._request_text(
            "POST",
            "transfer/setSpeedLimitsMode",
            data=data,
        )

    async def _set_speed_limits_mode_polyfill(self, mode: int):
        """
        This is a polyfill that ``speed_limits_mode`` is queried and
        toggled if needed.
        """

        new_mode = bool(mode)  # a bool is also an int
        old_mode = await self.speed_limits_mode()

        if old_mode != new_mode:
            await self.toggle_speed_limits_mode()

    async def download_limit(self) -> int:
        """Get download limit (byte/second)"""
        res = await self._request_text(
            "GET",
            "transfer/downloadLimit",
        )
        return int(res)

    async def set_download_limit(self, limit: int):
        """Set download limit (byte/second)"""
        _check_1024("limit", limit)

        data = ParamDict()
        data.required_int("limit", limit)

        await self._request_text(
            "POST",
            "transfer/setDownloadLimit",
            data=data,
        )

    async def upload_limit(self) -> int:
        """Get upload limit (byte/second)"""
        res = await self._request_text(
            "GET",
            "transfer/uploadLimit",
        )
        return int(res)

    async def set_upload_limit(self, limit: int):
        """Set upload limit (byte/second)"""
        _check_1024("limit", limit)

        data = ParamDict()
        data.required_int("limit", limit)

        await self._request_text(
            "POST",
            "transfer/setUploadLimit",
            data=data,
        )

    # since API v2.3.0
    async def ban_peers(
        self,
        peers: Iterable[Tuple[str, int]],
    ):
        """
        Ban peers.

        Address may be IPv4 or IPv6 but not domain name.

        :param peers: ``(addr, port)`` pairs
        """
        pairs = []

        for host, port in peers:
            pairs.append(f"{host!s}:{port:d}")

        data = ParamDict()
        data.required_list("peers", pairs, "|")

        await self._request_text(
            "POST",
            "transfer/banPeers",
            data=data,
        )
