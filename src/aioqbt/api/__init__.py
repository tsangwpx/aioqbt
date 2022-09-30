"""
API methods by group.

See also :APIWiki:`the WebUI API reference <>` on qBittorrent wiki.
"""

from aioqbt.api.app import AppAPI
from aioqbt.api.auth import AuthAPI
from aioqbt.api.log import LogAPI
from aioqbt.api.sync import SyncAPI
from aioqbt.api.torrents import AddFormBuilder, TorrentsAPI
from aioqbt.api.transfer import TransferAPI

__all__ = (
    "AddFormBuilder",
    "AppAPI",
    "AuthAPI",
    "LogAPI",
    "SyncAPI",
    "TorrentsAPI",
    "TransferAPI",
)
