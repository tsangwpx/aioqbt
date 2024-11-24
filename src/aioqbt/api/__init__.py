"""
API methods by group.

See also :APIWiki:`the WebUI API reference <>` on qBittorrent wiki.
"""

# re-export API groups, constants, and types here

from aioqbt.api.app import AppAPI as AppAPI
from aioqbt.api.auth import AuthAPI as AuthAPI
from aioqbt.api.log import LogAPI as LogAPI
from aioqbt.api.rss import RSSAPI as RSSAPI
from aioqbt.api.search import SearchAPI as SearchAPI
from aioqbt.api.sync import SyncAPI as SyncAPI
from aioqbt.api.torrents import AddFormBuilder as AddFormBuilder
from aioqbt.api.torrents import TorrentsAPI as TorrentsAPI
from aioqbt.api.transfer import TransferAPI as TransferAPI

# isort: split
from aioqbt.api.types import ConnectionStatus as ConnectionStatus
from aioqbt.api.types import ContentLayout as ContentLayout
from aioqbt.api.types import FilePriority as FilePriority
from aioqbt.api.types import InactiveSeedingTimeLimits as InactiveSeedingTimeLimits
from aioqbt.api.types import InfoFilter as InfoFilter
from aioqbt.api.types import PieceState as PieceState
from aioqbt.api.types import RatioLimits as RatioLimits
from aioqbt.api.types import SeedingTimeLimits as SeedingTimeLimits
from aioqbt.api.types import ShareLimitAction as ShareLimitAction
from aioqbt.api.types import StopCondition as StopCondition
from aioqbt.api.types import TorrentState as TorrentState
from aioqbt.api.types import TrackerStatus as TrackerStatus

# isort: split
from aioqbt.api.types import BuildInfo as BuildInfo
from aioqbt.api.types import Category as Category
from aioqbt.api.types import FileEntry as FileEntry
from aioqbt.api.types import LogMessage as LogMessage
from aioqbt.api.types import LogPeer as LogPeer
from aioqbt.api.types import NetworkInterface as NetworkInterface
from aioqbt.api.types import Preferences as Preferences
from aioqbt.api.types import RSSArticle as RSSArticle
from aioqbt.api.types import RSSFeed as RSSFeed
from aioqbt.api.types import RSSFolder as RSSFolder
from aioqbt.api.types import RSSItem as RSSItem
from aioqbt.api.types import RSSRule as RSSRule
from aioqbt.api.types import SearchJobResults as SearchJobResults
from aioqbt.api.types import SearchJobStart as SearchJobStart
from aioqbt.api.types import SearchJobStatus as SearchJobStatus
from aioqbt.api.types import SearchPlugin as SearchPlugin
from aioqbt.api.types import SearchPluginCategory as SearchPluginCategory
from aioqbt.api.types import SearchResultEntry as SearchResultEntry
from aioqbt.api.types import SyncCategory as SyncCategory
from aioqbt.api.types import SyncMainData as SyncMainData
from aioqbt.api.types import SyncPeer as SyncPeer
from aioqbt.api.types import SyncServerState as SyncServerState
from aioqbt.api.types import SyncTorrentInfo as SyncTorrentInfo
from aioqbt.api.types import SyncTorrentPeers as SyncTorrentPeers
from aioqbt.api.types import TorrentInfo as TorrentInfo
from aioqbt.api.types import TorrentProperties as TorrentProperties
from aioqbt.api.types import Tracker as Tracker
from aioqbt.api.types import TransferInfo as TransferInfo
from aioqbt.api.types import WebSeed as WebSeed
