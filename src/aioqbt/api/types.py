"""
Types utilized and returned by API methods.
"""
import enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union

from typing_extensions import TypedDict

from aioqbt._compat import IntEnum, StrEnum
from aioqbt.chrono import Minutes, TimeUnit
from aioqbt.converter import (
    DateTimeConverter,
    DurationConverter,
    EnumConverter,
    ScalarListConverter,
)


# define enums first
class TorrentState(StrEnum):
    """
    Torrent state to compare with :attr:`.TorrentInfo.state`.
    """

    ERROR = "error"
    MISSING_FILES = "missingFiles"
    UPLOADING = "uploading"
    PAUSED_UP = "pausedUP"
    QUEUED_UP = "queuedUP"
    STALLED_UP = "stalledUP"
    CHECKING_UP = "checkingUP"
    FORCED_UP = "forcedUP"
    ALLOCATING = "allocating"
    DOWNLOADING = "downloading"
    META_DL = "metaDL"
    PAUSED_DL = "pausedDL"
    QUEUED_DL = "queuedDL"
    STALLED_DL = "stalledDL"
    CHECKING_DL = "checkingDL"
    FORCED_DL = "forcedDL"
    CHECKING_RESUME_DATA = "checkingResumeData"
    MOVING = "moving"
    UNKNOWN = "unknown"


class InfoFilter(StrEnum):
    """
    Torrent ``filter`` in :meth:`.TorrentsAPI.info`.
    """

    ALL = "all"
    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    COMPLETED = "completed"
    RESUMED = "resumed"
    PAUSED = "paused"
    ACTIVE = "active"
    INACTIVE = "inactive"
    STALLED = "stalled"
    STALLED_UPLOADING = "stalled_uploading"
    STALLED_DOWNLOADING = "stalled_downloading"
    ERRORED = "errored"


class PieceState(IntEnum):
    """
    Piece state to compare with :meth:`.TorrentsAPI.piece_states` results.
    """

    UNAVAILABLE = 0
    DOWNLOADING = 1
    DOWNLOADED = 2


class TrackerStatus(IntEnum):
    """
    Tracker status  to compare with :attr:`.Tracker.status`.
    """

    DISABLED = 0
    NOT_CONTACTED = 1
    WORKING = 2
    UPDATING = 3
    NOT_WORKING = 4


class RatioLimits(IntEnum):
    """
    Special values of ratio limit.
    """

    UNSET = -1


RatioLimitTypes = Union[float, RatioLimits]


class SeedingTimeLimits(IntEnum):
    """
    Special values of seeding time limit.
    """

    GLOBAL = -2
    UNLIMITED = -1


SeedingTimeLimitTypes = Union[timedelta, Minutes, SeedingTimeLimits]


class FilePriority(IntEnum):
    """
    File priority to compare with :attr:`.FileEntry.priority`.
    """

    NO_DOWNLOAD = 0
    NORMAL = 1
    _DEFAULT = 4  # libtorrent defaults to 4, but invalid in bittorrent
    HIGH = 6
    MAXIMAL = 7


class ConnectionStatus(StrEnum):
    """
    Connection status to compare with :attr:`.TransferInfo.connection_status`.
    """

    CONNECTED = "connected"
    FIREWALLED = "firewalled"
    DISCONNECTED = "disconnected"


# values mapped to None
_DATETIME_NONE_TABLE = dict.fromkeys(
    (
        -1,
        0xFFFF_FFFF,  # -1 as u32
    )
)
_DURATION_NONE_TABLE = dict.fromkeys((-1,))
_E = TypeVar("_E", bound=enum.Enum)


def _table_from_enum(enum_type: Type[_E]) -> Dict[int, _E]:
    assert issubclass(enum_type, Enum) and issubclass(enum_type, int)
    return {int(s): s for s in enum_type.__members__.values()}


# define dataclasses after enums
@dataclass
class BuildInfo:
    """
    See :meth:`.AppAPI.build_info`.
    """

    qt: str
    libtorrent: str
    boost: str
    openssl: str
    zlib: str  # undocumented, found in API v2.5.1
    bitness: int


@dataclass
class TorrentInfo:
    """
    See :meth:`.TorrentsAPI.info`.
    """

    hash: str
    name: str
    added_on: datetime = field(
        metadata={
            "convert": DateTimeConverter(),  # unix timestamp
        }
    )
    amount_left: int
    auto_tmm: bool
    category: str
    completed: int
    completion_on: datetime = field(
        metadata={
            "convert": DateTimeConverter(),  # unix timestamp
        }
    )
    dl_limit: int
    dlspeed: int
    downloaded: int
    downloaded_session: int
    eta: timedelta
    f_l_piece_prio: bool
    force_start: bool
    last_activity: datetime = field(
        metadata={
            "convert": DateTimeConverter(),
        }
    )
    magnet_uri: str
    max_ratio: float
    # max_seeding_time is readonly
    max_seeding_time: Optional[timedelta] = field(
        metadata={
            "convert": DurationConverter(TimeUnit.MINUTES, _DURATION_NONE_TABLE),
        }
    )
    num_complete: int
    num_incomplete: int
    num_leechs: int
    num_seeds: int
    priority: int
    progress: float
    ratio: float
    ratio_limit: float
    save_path: str
    # seeding_time: int = field(
    #     metadata={
    #         "convert": DurationConverter(TimeUnit.SECONDS),
    #         "since": (2, 8, 1),
    #     }
    # )
    # seeding_time_limit is a setting, readwrite
    seeding_time_limit: SeedingTimeLimitTypes = field(
        metadata={
            "convert": DurationConverter(TimeUnit.MINUTES, _table_from_enum(SeedingTimeLimits)),
        }
    )
    seen_complete: datetime = field(
        metadata={
            "convert": DateTimeConverter(),
        }
    )
    seq_dl: bool
    size: int
    state: TorrentState = field(
        metadata={
            "convert": EnumConverter(TorrentState),
        }
    )
    super_seeding: bool
    tags: List[str] = field(
        metadata={
            "convert": ScalarListConverter(","),
        }
    )
    time_active: timedelta = field(
        metadata={
            "convert": DurationConverter(TimeUnit.SECONDS),
        }
    )
    total_size: int
    tracker: str
    up_limit: int
    uploaded: int
    uploaded_session: int
    upspeed: int

    availability: float
    content_path: Optional[str]  # since 2.6.1

    def __repr__(self):
        return f"<{type(self).__name__} {self.hash} {self.state.value} {self.name!r}>"


@dataclass
class TorrentProperties:
    """
    See :meth:`.TorrentsAPI.properties`.
    """

    save_path: str
    creation_date: Optional[datetime] = field(
        metadata={
            "convert": DateTimeConverter(_DATETIME_NONE_TABLE),
        }
    )
    piece_size: int
    comment: str
    total_wasted: int
    total_uploaded: int
    total_uploaded_session: int
    total_downloaded: int
    total_downloaded_session: int
    up_limit: int
    dl_limit: int
    # same as .TorrentInfo.active_time
    time_elapsed: timedelta = field(
        metadata={
            "convert": DurationConverter(TimeUnit.SECONDS),
        }
    )
    seeding_time: timedelta = field(
        metadata={
            "convert": DurationConverter(TimeUnit.MINUTES),
        }
    )
    nb_connections: int
    nb_connections_limit: int
    share_ratio: float
    addition_date: datetime = field(
        metadata={
            "convert": DateTimeConverter(),
        }
    )
    completion_date: Optional[datetime] = field(
        metadata={
            "convert": DateTimeConverter(_DATETIME_NONE_TABLE),
        }
    )
    created_by: str
    dl_speed_avg: int
    dl_speed: int
    # eta: timedelta
    last_seen: Optional[datetime] = field(
        metadata={
            "convert": DateTimeConverter(_DATETIME_NONE_TABLE),
        }
    )
    peers: int
    peers_total: int
    pieces_have: int
    pieces_num: int
    reannounce: timedelta = field(
        metadata={
            "convert": DurationConverter(TimeUnit.SECONDS),
        }
    )
    seeds: int
    seeds_total: int
    total_size: int
    up_speed_avg: int
    up_speed: int

    # hash is set by client to improve __repr__() only
    _hash: Optional[str] = field(default=None)

    def __repr__(self):
        cls_name = type(self).__name__

        try:
            h = self._hash
        except AttributeError:
            h = None

        if h is None:
            return f"<{cls_name} at {hex(id(self))}>"
        else:
            return f"<{cls_name} {h}>"


@dataclass
class Tracker:
    """
    See :meth:`.TorrentsAPI.trackers`.
    """

    url: str
    status: TrackerStatus = field(
        metadata={
            "convert": EnumConverter(TrackerStatus),
        }
    )
    tier: int
    num_peers: int
    num_seeds: int
    num_leeches: int
    num_downloaded: int
    msg: str

    def __repr__(self):
        cls_name = type(self).__name__
        title = self.url or ""
        msg = f" {self.msg!r}" if self.msg else ""

        if title.startswith("** [") and title.endswith("] **"):
            return f"<{cls_name} {title[4:-4]}{msg}>"
        else:
            return f"<{cls_name} {title!r}{msg}>"

    def is_special(self):
        url = self.url or ""
        return url.startswith("** [") and url.endswith("] **")


@dataclass
class WebSeed:
    """
    See :meth:`.TorrentsAPI.webseeds`.
    """

    url: str


@dataclass
class FileEntry:
    """
    See :meth:`.TorrentsAPI.files`.
    """

    name: str
    size: int
    progress: float
    priority: Union[int, FilePriority]
    piece_range: Tuple[int, int]
    is_seed: bool = field(repr=False)  # only available in the first item
    availability: float
    index: int = field(repr=False)  # since API v2.8.2


@dataclass
class Category:
    """
    See :meth:`.TorrentsAPI.categories`.
    """

    name: str
    savePath: str


@dataclass
class LogMessage:
    """
    See :meth:`.LogAPI.main`.
    """

    id: int
    message: str
    timestamp: int
    type: int


@dataclass
class LogPeer:
    """
    See :meth:`.LogAPI.peers`.
    """

    id: int
    ip: str
    timestamp: int
    blocked: bool
    reason: str


class SyncTorrentInfo(TypedDict, total=False):
    """
    See :class:`.SyncMainData`.
    """

    name: str
    size: int
    progress: float
    dlspeed: int
    upspeed: int
    priority: int
    num_seeds: int
    num_complete: int
    num_leechs: int
    num_incomplete: int
    ratio: float
    eta: Any
    state: str
    seq_dl: bool
    f_l_piece_prio: bool
    completion_on: int
    tracker: str
    dl_limit: int
    up_limit: int
    downloaded: int
    uploaded: int
    downloaded_session: int
    uploaded_session: int
    amount_left: int
    save_path: str
    completed: int
    max_ratio: float
    max_seeding_time: int
    ratio_limit: float
    seeding_time_limit: int
    seen_complete: int
    last_activity: int
    total_size: int


class SyncCategory(TypedDict, total=False):
    """
    See :class:`.SyncMainData`.
    """

    name: str
    savePath: str


class SyncServerState(TypedDict, total=False):
    """
    See :class:`.SyncMainData`.
    """

    connection_status: str
    dht_nodes: int
    dl_info_data: int
    dl_info_speed: int
    dl_rate_limit: int
    up_info_data: int
    up_info_speed: int
    up_rate_limit: int
    queueing: bool
    refresh_interval: int
    free_space_on_disk: int


@dataclass
class SyncMainData:
    """
    See :meth:`.SyncAPI.maindata`.
    """

    rid: int
    full_update: bool = field(
        metadata={
            "default": False,
        }
    )
    torrents: Dict[str, SyncTorrentInfo] = field(
        metadata={
            "default_factory": dict,
        }
    )
    torrents_removed: List[str] = field(
        metadata={
            "default_factory": list,
        }
    )
    categories: Dict[str, SyncCategory] = field(
        metadata={
            "default_factory": dict,
        }
    )
    categories_removed: List[str] = field(
        metadata={
            "default_factory": list,
        }
    )
    server_state: SyncServerState = field(
        metadata={
            "default_factory": SyncServerState,
        }
    )


class SyncPeer(TypedDict, total=False):
    """
    See :class:`.SyncTorrentPeers`.
    """

    ip: str
    port: int
    client: str
    progress: float
    dl_speed: int
    up_speed: int
    downloaded: int
    uploaded: int
    connection: str
    flags: str
    flags_desc: str
    relevance: float
    files: str
    country_code: str
    country: str


@dataclass
class SyncTorrentPeers:
    """
    See :meth:`.SyncAPI.torrent_peers`.
    """

    rid: int
    full_update: bool = field(
        metadata={
            "default": False,
        }
    )
    # "show_flags" may be true, false or missing
    show_flags: Optional[bool] = field(
        metadata={
            "default": None,
        }
    )
    peers: Dict[str, SyncPeer] = field(
        metadata={
            "default_factory": dict,
        }
    )


@dataclass
class TransferInfo:
    """
    See :meth:`.TransferAPI.info`.
    """

    dl_info_speed: int
    dl_info_data: int
    up_info_speed: int
    up_info_data: int
    dl_rate_limit: int
    up_rate_limit: int
    dht_nodes: int

    connection_status: ConnectionStatus = field(
        metadata={
            "convert": EnumConverter(ConnectionStatus),
        }
    )
