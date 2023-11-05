"""
API methods by group.

See also :APIWiki:`the WebUI API reference <>` on qBittorrent wiki.
"""

# re-export API groups, constants, and types here

from aioqbt.api.app import AppAPI
from aioqbt.api.auth import AuthAPI
from aioqbt.api.log import LogAPI
from aioqbt.api.sync import SyncAPI
from aioqbt.api.torrents import AddFormBuilder, TorrentsAPI
from aioqbt.api.transfer import TransferAPI

# isort: split
from aioqbt.api.types import (
    ConnectionStatus,
    ContentLayout,
    FilePriority,
    InactiveSeedingTimeLimits,
    InfoFilter,
    PieceState,
    RatioLimits,
    SeedingTimeLimits,
    StopCondition,
    TorrentState,
    TrackerStatus,
)

# isort: split
from aioqbt.api.types import (
    BuildInfo,
    Category,
    FileEntry,
    LogMessage,
    LogPeer,
    NetworkInterface,
    Preferences,
    SyncCategory,
    SyncMainData,
    SyncPeer,
    SyncServerState,
    SyncTorrentInfo,
    SyncTorrentPeers,
    TorrentInfo,
    TorrentProperties,
    Tracker,
    TransferInfo,
    WebSeed,
)

# wildcard imports are discouraged
__all__ = (
    "AddFormBuilder",
    "AppAPI",
    "AuthAPI",
    "LogAPI",
    "SyncAPI",
    "TorrentsAPI",
    "TransferAPI",
)
