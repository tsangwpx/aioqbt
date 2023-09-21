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
    Possible torrent states in :attr:`.TorrentInfo.state`.
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
    Torrent state filter in :meth:`.TorrentsAPI.info`.
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
    Piece state in :meth:`.TorrentsAPI.piece_states` results.
    """

    UNAVAILABLE = 0
    DOWNLOADING = 1
    DOWNLOADED = 2


class TrackerStatus(IntEnum):
    """
    Tracker status in :attr:`.Tracker.status`.
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


class StopCondition(StrEnum):
    """
    Stopping condition to pause torrents.
    """

    NONE = "None"
    METADATA_RECEIVED = "MetadataReceived"
    FILES_CHECKED = "FilesChecked"


class ContentLayout(StrEnum):
    """
    Content layout that downloaded files are organized.
    """

    ORIGINAL = "Original"
    SUBFOLDER = "Subfolder"
    NO_SUBFOLDER = "NoSubfolder"


class FilePriority(IntEnum):
    """
    File priority in :meth:`.TorrentsAPI.file_prio` and :attr:`.FileEntry.priority`.
    """

    NO_DOWNLOAD = 0
    NORMAL = 1
    _DEFAULT = 4  # libtorrent defaults to 4, but invalid in bittorrent
    HIGH = 6
    MAXIMAL = 7


class ConnectionStatus(StrEnum):
    """
    Connection status in :attr:`.TransferInfo.connection_status`.
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


class Preferences(TypedDict, total=False):
    """
    Dict of preferences.

    .. note::

        Preference keys may be added/changed/removed across versions.
        Please refer to :APIWiki:`the documentation <#get-application-preferences>`.

    """

    locale: str
    performance_warning: bool

    file_log_enabled: bool
    file_log_path: str
    file_log_backup_enabled: bool
    file_log_max_size: int
    file_log_delete_old: bool
    file_log_age: int
    file_log_age_type: str

    torrent_content_layout: str
    add_to_top_of_queue: bool
    create_subfolder_enabled: bool  # removed in v4.3.2
    start_paused_enabled: bool
    torrent_stop_condition: str
    merge_trackers: bool
    auto_delete_mode: int
    preallocate_all: bool
    incomplete_files_ext: bool

    auto_tmm_enabled: bool
    torrent_changed_tmm_enabled: bool
    save_path_changed_tmm_enabled: bool
    category_changed_tmm_enabled: bool
    use_subcategories: bool
    save_path: str
    temp_path_enabled: bool
    temp_path: str
    use_category_paths_in_manual_mode: bool
    export_dir: str
    export_dir_fin: str

    scan_dirs: Dict[str, Union[int, str]]

    excluded_file_names_enabled: bool
    excluded_file_names: str

    mail_notification_enabled: bool
    mail_notification_sender: str
    mail_notification_email: str
    mail_notification_smtp: str
    mail_notification_ssl_enabled: bool
    mail_notification_auth_enabled: bool
    mail_notification_username: str
    mail_notification_password: str

    autorun_on_torrent_added_enabled: bool
    autorun_on_torrent_added_program: str

    autorun_enabled: bool
    autorun_program: str

    listen_port: int
    random_port: bool
    upnp: bool

    max_connec: int
    max_connec_per_torrent: int
    max_uploads: int
    max_uploads_per_torrent: int

    proxy_type: int
    proxy_ip: str
    proxy_port: int
    proxy_auth_enabled: bool
    proxy_username: str
    proxy_password: str
    proxy_hostname_lookup: bool
    proxy_torrents_only: bool
    proxy_peer_connections: bool

    ip_filter_enabled: bool
    ip_filter_path: str
    ip_filter_trackers: bool
    banned_IPs: str

    dl_limit: int
    up_limit: int
    alt_dl_limit: int
    alt_up_limit: int
    bittorrent_protocol: int
    limit_utp_rate: bool
    limit_tcp_overhead: bool
    limit_lan_peers: bool

    scheduler_enabled: bool
    schedule_from_hour: int
    schedule_from_min: int
    schedule_to_hour: int
    schedule_to_min: int
    scheduler_days: int

    dht: bool
    pex: bool
    lsd: bool
    encryption: int
    anonymous_mode: bool

    max_active_checking_torrents: int

    queueing_enabled: bool
    max_active_downloads: int
    max_active_torrents: int
    max_active_uploads: int
    dont_count_slow_torrents: bool
    slow_torrent_dl_rate_threshold: int
    slow_torrent_ul_rate_threshold: int
    slow_torrent_inactive_timer: int

    max_ratio_enabled: bool
    max_ratio: int
    max_seeding_time_enabled: bool
    max_seeding_time: int
    max_ratio_act: int

    add_trackers_enabled: bool
    add_trackers: str

    web_ui_domain_list: str
    web_ui_address: str
    web_ui_port: int
    web_ui_upnp: bool
    use_https: bool
    web_ui_https_cert_path: str
    web_ui_https_key_path: str

    web_ui_username: str
    bypass_local_auth: bool
    bypass_auth_subnet_whitelist_enabled: bool
    bypass_auth_subnet_whitelist: str
    web_ui_max_auth_fail_count: int
    web_ui_ban_duration: int
    web_ui_session_timeout: int

    alternative_webui_enabled: bool
    alternative_webui_path: str

    web_ui_clickjacking_protection_enabled: bool
    web_ui_csrf_protection_enabled: bool
    web_ui_secure_cookie_enabled: bool
    web_ui_host_header_validation_enabled: bool

    web_ui_use_custom_http_headers_enabled: bool
    web_ui_custom_http_headers: str

    web_ui_reverse_proxy_enabled: bool
    web_ui_reverse_proxies_list: str

    dyndns_enabled: bool
    dyndns_service: int
    dyndns_username: str
    dyndns_password: str
    dyndns_domain: str

    # rss
    rss_refresh_interval: int
    rss_max_articles_per_feed: int
    rss_processing_enabled: bool
    rss_auto_downloading_enabled: bool
    rss_download_repack_proper_episodes: bool
    rss_smart_episode_filters: str

    # advanced
    resume_data_storage_type: str
    memory_working_set_limit: int
    current_network_interface: str
    current_interface_address: str
    save_resume_data_interval: int
    recheck_completed_torrents: bool
    refresh_interval: int
    resolve_peer_countries: bool
    reannounce_when_address_changed: bool

    # libtorrent
    async_io_threads: int
    hashing_threads: int
    file_pool_size: int
    checking_memory_use: int
    disk_cache: int
    disk_cache_ttl: int
    disk_queue_size: int
    disk_io_type: int
    disk_io_read_mode: int
    disk_io_write_mode: int
    enable_os_cache: bool  # removed
    enable_coalesce_read_write: bool
    enable_piece_extent_affinity: bool
    enable_upload_suggestions: bool
    send_buffer_watermark: int
    send_buffer_low_watermark: int
    send_buffer_watermark_factor: int
    connection_speed: int
    socket_backlog_size: int
    outgoing_ports_min: int
    outgoing_ports_max: int
    upnp_lease_duration: int
    peer_tos: int
    utp_tcp_mixed_mode: int
    idn_support_enabled: bool
    enable_multi_connections_from_same_ip: bool
    validate_https_tracker_certificate: bool
    ssrf_mitigation: bool
    block_peers_on_privileged_ports: bool
    enable_embedded_tracker: bool
    embedded_tracker_port: int
    embedded_tracker_port_forwarding: bool
    upload_slots_behavior: int
    upload_choking_algorithm: int
    announce_to_all_trackers: bool
    announce_to_all_tiers: bool
    announce_ip: str
    max_concurrent_http_announces: int
    stop_tracker_timeout: int
    peer_turnover: int
    peer_turnover_cutoff: int
    peer_turnover_interval: int
    request_queue_size: int

    # removed keys
    force_proxy: bool
    ssl_cert: str
    ssl_key: str
    web_ui_password: str


@dataclass
class NetworkInterface:
    """
    See :meth:`.AppAPI.network_interface_list`.
    """

    name: str
    value: str


@dataclass
class TorrentInfo:
    """
    Obtained from :meth:`.TorrentsAPI.info`.

    Also see :APIWiki:`qBittorrent Wiki <#get-torrent-list>` for attribute meanings.

    .. include:: shared/missing_attributes.rst
    """

    hash: str
    """Torrent ID (info hash)"""

    infohash_v1: str  # API 2.8.4
    infohash_v2: str  # API 2.8.4
    """``infohash_v1`` and ``infohash_v2`` are available since v4.4.0"""

    name: str
    """Torrent name."""

    magnet_uri: str
    size: int
    progress: float
    dlspeed: int
    upspeed: int
    priority: int
    num_seeds: int
    num_complete: int
    num_leechs: int
    num_incomplete: int

    state: TorrentState = field(
        metadata={
            "convert": EnumConverter(TorrentState),
        }
    )
    eta: timedelta = field(
        metadata={
            "convert": DurationConverter(TimeUnit.SECONDS),
        }
    )
    seq_dl: bool
    f_l_piece_prio: bool

    category: str
    tags: List[str] = field(
        metadata={
            "convert": ScalarListConverter(","),
        }
    )
    super_seeding: bool
    force_start: bool
    save_path: str
    download_path: str  # API v2.8.4
    content_path: str  # API v2.6.1
    added_on: datetime = field(
        metadata={
            "convert": DateTimeConverter(),  # unix timestamp
        }
    )
    completion_on: datetime = field(
        metadata={
            "convert": DateTimeConverter(),  # unix timestamp
        }
    )
    tracker: str
    trackers_count: int
    dl_limit: int
    up_limit: int
    downloaded: int
    uploaded: int
    downloaded_session: int
    uploaded_session: int
    amount_left: int
    completed: int
    max_ratio: float
    max_seeding_time: Optional[timedelta] = field(
        metadata={
            "convert": DurationConverter(TimeUnit.MINUTES, _DURATION_NONE_TABLE),
        }
    )
    ratio: float
    ratio_limit: float
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
    auto_tmm: bool
    time_active: timedelta = field(
        metadata={
            "convert": DurationConverter(TimeUnit.SECONDS),
        }
    )
    seeding_time: timedelta = field(
        metadata={
            "convert": DurationConverter(TimeUnit.SECONDS),
        }
    )
    last_activity: datetime = field(
        metadata={
            "convert": DateTimeConverter(),
        }
    )
    availability: float

    total_size: int

    def __repr__(self):
        return f"<{type(self).__name__} {self.hash} {self.state.value} {self.name!r}>"


@dataclass
class TorrentProperties:
    """
    Obtained from :meth:`.TorrentsAPI.properties`.

    .. include:: shared/missing_attributes.rst
    """

    infohash_v1: str  # API v2.8.3
    infohash_v2: str  # API v2.8.3
    """``infohash_v1`` and ``infohash_v2`` are available since v4.4.0"""

    name: str  # API v2.8.19
    hash: str  # API v2.8.19
    """``name`` and ``hash`` are available since v4.5.2"""

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
    eta: timedelta = field(
        metadata={
            "convert": DurationConverter(TimeUnit.SECONDS),
        }
    )
    nb_connections: int
    nb_connections_limit: int
    total_downloaded: int
    total_downloaded_session: int
    total_uploaded: int
    total_uploaded_session: int
    dl_speed: int
    dl_speed_avg: int
    up_speed: int
    up_speed_avg: int
    dl_limit: int
    up_limit: int
    total_wasted: int
    seeds: int
    seeds_total: int
    peers: int
    peers_total: int
    share_ratio: float
    reannounce: timedelta = field(
        metadata={
            "convert": DurationConverter(TimeUnit.SECONDS),
        }
    )
    total_size: int
    pieces_num: int
    piece_size: int
    pieces_have: int
    created_by: str
    is_private: bool  # v2.8.20
    addition_date: datetime = field(
        metadata={
            "convert": DateTimeConverter(),
        }
    )

    last_seen: Optional[datetime] = field(
        metadata={
            "convert": DateTimeConverter(_DATETIME_NONE_TABLE),
        }
    )
    completion_date: Optional[datetime] = field(
        metadata={
            "convert": DateTimeConverter(_DATETIME_NONE_TABLE),
        }
    )
    creation_date: Optional[datetime] = field(
        metadata={
            "convert": DateTimeConverter(_DATETIME_NONE_TABLE),
        }
    )

    save_path: str
    download_path: str  # v2.8.4
    comment: str

    def __repr__(self):
        cls_name = type(self).__name__

        name = getattr(self, "name", None)
        hash = getattr(self, "hash", None)

        if name is None and hash is None:
            return f"<{cls_name} at 0x{hex(id(self))}>"
        else:
            return f"<{cls_name} hash={hash!s} name={name!r}>"


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
    Dict of torrent info in :attr:`.SyncMainData.torrents`.
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
    Dict of category properties in :attr:`.SyncMainData.categories`.
    """

    name: str
    savePath: str


class SyncServerState(TypedDict, total=False):
    """
    Dict of qBittorrent status and statistics in :attr:`.SyncMainData.server_state`.
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
    Sync results obtained from :meth:`.SyncAPI.maindata`.
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
    Dict of peer info in :attr:`.SyncTorrentPeers.peers`.
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
