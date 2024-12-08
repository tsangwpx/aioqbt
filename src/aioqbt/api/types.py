"""
Types utilized and returned by API methods.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Iterator, List, Mapping, Optional, Type, TypeVar, Union, overload

from typing_extensions import Annotated, Final, Literal, TypedDict

from aioqbt._compat import IntEnum, StrEnum
from aioqbt.chrono import Minutes, TimeUnit
from aioqbt.converter import (
    DateTimeConverter,
    DurationConverter,
    EnumConverter,
    RFC2822DateTimeConverter,
    ScalarListConverter,
)
from aioqbt.mapper import declarative, field


# define enums first
class TorrentState(StrEnum):
    """
    Possible torrent states in :attr:`.TorrentInfo.state`.
    """

    ERROR = "error"
    MISSING_FILES = "missingFiles"
    UPLOADING = "uploading"
    STOPPED_UP = "stoppedUP"
    QUEUED_UP = "queuedUP"
    STALLED_UP = "stalledUP"
    CHECKING_UP = "checkingUP"
    FORCED_UP = "forcedUP"
    ALLOCATING = "allocating"
    DOWNLOADING = "downloading"
    META_DL = "metaDL"
    STOPPED_DL = "stoppedDL"
    QUEUED_DL = "queuedDL"
    STALLED_DL = "stalledDL"
    CHECKING_DL = "checkingDL"
    FORCED_DL = "forcedDL"
    CHECKING_RESUME_DATA = "checkingResumeData"
    MOVING = "moving"
    UNKNOWN = "unknown"

    # PAUSED_UP and PAUSED_DL were used in qBittorrent 4.x series
    # they are replaced by STOPPED_UP and STOPPED_DL respectively in 5.x series
    PAUSED_UP = "pausedUP"
    PAUSED_DL = "pausedDL"

    def is_checking(self) -> bool:
        """
        Return ``True`` if the state is

        * :attr:`.CHECKING_DL`
        * :attr:`.CHECKING_UP`
        * :attr:`.CHECKING_RESUME_DATA`
        """

        return self in _CHECKING_STATES

    def is_downloading(self) -> bool:
        """
        Return ``True`` if the state is

        * :attr:`.DOWNLOADING`
        * :attr:`.META_DL`
        * :attr:`.STOPPED_DL`
        * :attr:`.QUEUED_DL`
        * :attr:`.STALLED_DL`
        * :attr:`.CHECKING_DL`
        * :attr:`.FORCED_DL`
        * :attr:`.PAUSED_DL`
        """

        return self in _DOWNLOADING_STATES

    def is_uploading(self) -> bool:
        """
        Return ``True`` if the state is

        * :attr:`.UPLOADING`
        * :attr:`.STALLED_UP`
        * :attr:`.CHECKING_UP`
        * :attr:`.QUEUED_UP`
        * :attr:`.FORCED_UP`
        """

        return self in _UPLOADING_STATES

    def is_completed(self) -> bool:
        """
        Return ``True`` if the state is

        * :attr:`.UPLOADING`
        * :attr:`.STALLED_UP`
        * :attr:`.CHECKING_UP`
        * :attr:`.STOPPED_UP`
        * :attr:`.QUEUED_UP`
        * :attr:`.FORCED_UP`
        """

        return self in _COMPLETED_STATES

    def is_errored(self) -> bool:
        """
        Return ``True`` if the state is

        * :attr:`.ERROR`
        * :attr:`.MISSING_FILES`
        """

        return self in _ERRORED_STATES

    def is_stopped(self) -> bool:
        """
        Return ``True`` if the state is

        * :attr:`.STOPPED_UP`
        * :attr:`.STOPPED_DL`
        * :attr:`.PAUSED_UP`
        * :attr:`.PAUSED_DL`
        """

        return self in _STOPPED_STATES

    is_paused = is_stopped


_CHECKING_STATES = frozenset(
    (
        TorrentState.CHECKING_DL,
        TorrentState.CHECKING_UP,
        TorrentState.CHECKING_RESUME_DATA,
    )
)

_DOWNLOADING_STATES = frozenset(
    {
        TorrentState.DOWNLOADING,
        TorrentState.META_DL,
        TorrentState.STOPPED_DL,
        TorrentState.QUEUED_DL,
        TorrentState.STALLED_DL,
        TorrentState.CHECKING_DL,
        TorrentState.FORCED_DL,
        TorrentState.PAUSED_DL,
    }
)

_UPLOADING_STATES = frozenset(
    {
        TorrentState.UPLOADING,
        TorrentState.STALLED_UP,
        TorrentState.CHECKING_UP,
        TorrentState.QUEUED_UP,
        TorrentState.FORCED_UP,
    }
)

_COMPLETED_STATES = frozenset(
    {
        TorrentState.UPLOADING,
        TorrentState.STALLED_UP,
        TorrentState.CHECKING_UP,
        TorrentState.STOPPED_UP,
        TorrentState.QUEUED_UP,
        TorrentState.FORCED_UP,
    }
)

_ERRORED_STATES = frozenset(
    {
        TorrentState.ERROR,
        TorrentState.MISSING_FILES,
    }
)

_STOPPED_STATES = frozenset(
    {
        TorrentState.STOPPED_UP,
        TorrentState.STOPPED_DL,
        TorrentState.PAUSED_UP,
        TorrentState.PAUSED_DL,
    }
)


class InfoFilter(StrEnum):
    """
    Torrent state filter in :meth:`.TorrentsAPI.info`.

    :attr:`.RESUMED` and :attr:`.PAUSED` are removed in qBittorrent v5.
    Please migrate to :attr:`.RUNNING` and :attr:`.PAUSED` respectively.
    """

    ALL = "all"
    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    COMPLETED = "completed"
    RUNNING = "running"
    STOPPED = "stopped"
    ACTIVE = "active"
    INACTIVE = "inactive"
    STALLED = "stalled"
    STALLED_UPLOADING = "stalled_uploading"
    STALLED_DOWNLOADING = "stalled_downloading"
    CHECKING = "checking"
    MOVING = "moving"
    ERRORED = "errored"

    RESUMED = "resumed"
    PAUSED = "paused"


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


class InactiveSeedingTimeLimits(IntEnum):
    GLOBAL = -2
    UNLIMITED = -1


InactiveSeedingTimeLimitTypes = Union[timedelta, Minutes, InactiveSeedingTimeLimits]


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


class ShareLimitAction(IntEnum):
    DEFAULT = -1
    STOP = 0
    REMOVE = 1
    ENABLE_SUPER_SEEDING = 2
    REMOVE_WITH_CONTENT = 3


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
_IE = TypeVar("_IE", bound=IntEnum)
_SE = TypeVar("_SE", bound=StrEnum)


@overload
def _table_from_enum(cls: Type[_IE]) -> Dict[int, _IE]: ...


@overload
def _table_from_enum(cls: Type[_SE]) -> Dict[str, _SE]: ...


def _table_from_enum(cls: Union[Type[IntEnum], Type[StrEnum]]) -> Dict[Any, Any]:
    if issubclass(cls, IntEnum):
        return {int(s): s for s in cls.__members__.values()}
    elif issubclass(cls, StrEnum):
        return {str(s): s for s in cls.__members__.values()}
    else:
        raise AssertionError("unreachable")


# define dataclasses after enums
@declarative
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
    platform: Literal["linux", "macos", "windows", "unknown"]  # API v2.10.3


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
    file_log_age_type: int
    delete_torrent_content_files: bool  # API v2.10.2

    torrent_content_layout: str
    add_to_top_of_queue: bool
    create_subfolder_enabled: bool  # removed in v4.3.2
    start_paused_enabled: bool  # removed in API v2.11.0, replaced by add_stopped_enabled
    add_stopped_enabled: bool  # API v2.11.0
    torrent_stop_condition: str
    merge_trackers: bool
    auto_delete_mode: int
    preallocate_all: bool
    incomplete_files_ext: bool
    use_unwanted_folder: bool

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
    ssl_enabled: bool  # API v2.10.4
    ssl_listen_port: int  # API v2.10.4
    random_port: bool
    upnp: bool

    max_connec: int
    max_connec_per_torrent: int
    max_uploads: int
    max_uploads_per_torrent: int

    # I2P, since API v2.9.6
    i2p_enabled: bool
    i2p_address: str
    i2p_port: int
    i2p_mixed_mode: bool
    i2p_inbound_quantity: int
    i2p_outbound_quantity: int
    i2p_inbound_length: int
    i2p_outbound_length: int

    proxy_type: Union[int, str]  # int -> str in v4.6.0
    proxy_ip: str
    proxy_port: int
    proxy_auth_enabled: bool
    proxy_username: str
    proxy_password: str
    proxy_hostname_lookup: bool

    proxy_bittorrent: bool  # found in v4.6.0
    proxy_torrents_only: bool
    proxy_peer_connections: bool
    proxy_rss: bool  # found in v4.6.0
    proxy_misc: bool  # found in v4.6.0

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
    max_inactive_seeding_time_enabled: bool  # 4.6.0
    max_inactive_seeding_time: int  # 4.6.0
    max_ratio_act: Annotated[int, ShareLimitAction]

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
    rss_fetch_delay: int  # API v2.10.3
    rss_max_articles_per_feed: int
    rss_processing_enabled: bool
    rss_auto_downloading_enabled: bool
    rss_download_repack_proper_episodes: bool
    rss_smart_episode_filters: str

    # advanced
    resume_data_storage_type: str
    torrent_content_remove_option: str  # API v2.11.2
    memory_working_set_limit: int
    current_network_interface: str
    current_interface_name: str  # v4.6.0
    current_interface_address: str
    save_resume_data_interval: int
    torrent_file_size_limit: int
    recheck_completed_torrents: bool
    app_instance_name: str  # API v2.10.4
    refresh_interval: int
    resolve_peer_countries: bool
    reannounce_when_address_changed: bool

    # libtorrent
    bdecode_depth_limit: int
    bdecode_token_limit: int
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
    socket_send_buffer_size: int  # found in v4.6.0
    socket_receive_buffer_size: int  # found in v4.6.0
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
    mark_of_the_web: bool  # API v2.10.1
    ignore_ssl_errors: bool  # API v2.11.2?
    python_executable_path: str  # API v2.9.5
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
    dht_bootstrap_nodes: str  # API v2.9.4

    # removed keys
    force_proxy: bool
    ssl_cert: str
    ssl_key: str
    web_ui_password: str


@declarative
class NetworkInterface:
    """
    See :meth:`.AppAPI.network_interface_list`.
    """

    name: str
    value: str


@declarative
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

    state: Union[str, TorrentState] = field(
        convert=EnumConverter(TorrentState),
    )
    eta: timedelta = field(
        convert=DurationConverter(TimeUnit.SECONDS),
    )
    seq_dl: bool
    f_l_piece_prio: bool

    category: str
    tags: List[str] = field(
        convert=ScalarListConverter(","),
    )
    super_seeding: bool
    force_start: bool
    save_path: str
    download_path: str  # API v2.8.4
    content_path: str  # API v2.6.1
    root_path: str  # API v2.11.2
    added_on: datetime = field(
        convert=DateTimeConverter(),  # unix timestamp
    )
    completion_on: datetime = field(
        convert=DateTimeConverter(),  # unix timestamp
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
        convert=DurationConverter(TimeUnit.MINUTES, _DURATION_NONE_TABLE),
    )
    max_inactive_seeding_time: Optional[timedelta] = field(
        convert=DurationConverter(TimeUnit.MINUTES, _DURATION_NONE_TABLE),
    )
    ratio: float
    ratio_limit: Union[float, RatioLimits]
    popularity: float  # API v2.11.1
    seeding_time_limit: Union[timedelta, int, SeedingTimeLimits] = field(
        convert=DurationConverter(TimeUnit.MINUTES, _table_from_enum(SeedingTimeLimits)),
    )
    inactive_seeding_time_limit: Union[timedelta, int, InactiveSeedingTimeLimits] = field(
        convert=DurationConverter(TimeUnit.MINUTES, _table_from_enum(SeedingTimeLimits)),
    )
    seen_complete: datetime = field(
        convert=DateTimeConverter(),
    )
    auto_tmm: bool
    time_active: timedelta = field(
        convert=DurationConverter(TimeUnit.SECONDS),
    )
    seeding_time: timedelta = field(
        convert=DurationConverter(TimeUnit.SECONDS),
    )
    last_activity: datetime = field(
        convert=DateTimeConverter(),
    )
    availability: float
    reannounce: timedelta = field(
        # API v2.9.3
        convert=DurationConverter(TimeUnit.SECONDS),
    )
    comment: str  # API v2.10.2
    private: bool  # API v2.11.1
    has_metadata: bool  # API v2.11.2
    total_size: int

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.hash} {self.state} {self.name!r}>"


@declarative
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
        convert=DurationConverter(TimeUnit.SECONDS),
    )
    seeding_time: timedelta = field(
        convert=DurationConverter(TimeUnit.MINUTES),
    )
    eta: timedelta = field(
        convert=DurationConverter(TimeUnit.SECONDS),
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
    popularity: float  # API v2.11.1
    reannounce: timedelta = field(
        convert=DurationConverter(TimeUnit.SECONDS),
    )
    total_size: int
    pieces_num: int
    piece_size: int
    pieces_have: int
    created_by: str
    is_private: bool  # v2.8.20
    private: bool  # API v2.11.1
    addition_date: datetime = field(
        convert=DateTimeConverter(),
    )

    last_seen: Optional[datetime] = field(
        convert=DateTimeConverter(_DATETIME_NONE_TABLE),
    )
    completion_date: Optional[datetime] = field(
        convert=DateTimeConverter(_DATETIME_NONE_TABLE),
    )
    creation_date: Optional[datetime] = field(
        convert=DateTimeConverter(_DATETIME_NONE_TABLE),
    )

    save_path: str
    download_path: str  # v2.8.4
    comment: str
    has_metadata: bool  # API v2.11.2

    def __repr__(self) -> str:
        cls_name = type(self).__name__

        name = getattr(self, "name", None)
        hash = getattr(self, "hash", None)

        if name is None and hash is None:
            return f"<{cls_name} at 0x{hex(id(self))}>"
        else:
            return f"<{cls_name} hash={hash!s} name={name!r}>"


@declarative
class Tracker:
    """
    See :meth:`.TorrentsAPI.trackers`.
    """

    url: str
    status: Union[int, TrackerStatus] = field(
        convert=EnumConverter(TrackerStatus),
    )
    tier: int
    num_peers: int
    num_seeds: int
    num_leeches: int
    num_downloaded: int
    msg: str

    def __repr__(self) -> str:
        cls_name = type(self).__name__
        title = self.url or ""
        msg = f" {self.msg!r}" if self.msg else ""

        if title.startswith("** [") and title.endswith("] **"):
            return f"<{cls_name} {title[4:-4]}{msg}>"
        else:
            return f"<{cls_name} {title!r}{msg}>"

    def is_special(self) -> bool:
        url = self.url or ""
        return url.startswith("** [") and url.endswith("] **")


@declarative
class WebSeed:
    """
    See :meth:`.TorrentsAPI.webseeds`.
    """

    url: str


@declarative
class FileEntry:
    """
    See :meth:`.TorrentsAPI.files`.
    """

    name: str
    size: int
    progress: float
    priority: Union[int, FilePriority]
    piece_range: List[int]
    is_seed: bool = field(repr=False)  # only available in the first item
    availability: float
    index: int = field(repr=False)  # since API v2.8.2


@declarative
class Category:
    """
    See :meth:`.TorrentsAPI.categories`.
    """

    name: str
    savePath: str


@declarative
class TorrentSSLParameters:
    """
    See :meth:`.TorrentsAPI.ssl_parameters`.
    """

    ssl_certificate: str
    ssl_private_key: str
    ssl_dh_params: str


@declarative
class LogMessage:
    """
    See :meth:`.LogAPI.main`.
    """

    id: int
    message: str
    timestamp: int
    type: int


@declarative
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

    # This type and TorrentInfo share mostly identical set of keys
    # Annotations are more primordial here.

    # Due to difference algorithm, "hash" is always filtered out.
    # hash: str

    infohash_v1: str
    infohash_v2: str

    name: str
    size: int

    magnet_uri: str
    progress: float
    dlspeed: int
    upspeed: int
    priority: int
    num_seeds: int
    num_complete: int
    num_leechs: int
    num_incomplete: int

    state: str
    eta: int
    seq_dl: bool
    f_l_piece_prio: bool

    category: str
    tags: str
    super_seeding: bool
    force_start: bool
    save_path: str
    download_path: str
    content_path: str
    root_path: str  # API v2.11.2
    added_on: int
    completion_on: int
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
    max_seeding_time: int
    max_inactive_seeding_time: int
    ratio: float
    ratio_limit: float
    popularity: float  # API v2.11.1
    seeding_time_limit: int
    inactive_seeding_time_limit: int
    seen_complete: int
    auto_tmm: bool
    time_active: int
    seeding_time: int
    last_activity: int
    availability: float
    reannounce: int  # API v2.9.3
    comment: str  # API v2.10.2
    private: bool  # API v2.11.1
    has_metadata: bool  # API v2.11.2
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

    connection_status: Union[str, ConnectionStatus]
    dht_nodes: int
    dl_info_data: int
    dl_info_speed: int
    dl_rate_limit: int
    up_info_data: int
    up_info_speed: int
    up_rate_limit: int

    alltime_dl: int
    alltime_ul: int
    total_wasted_session: int
    global_ratio: str
    total_peer_connections: int

    queueing: bool
    use_alt_speed_limits: bool
    refresh_interval: int
    free_space_on_disk: int
    use_subcategories: bool

    average_time_queue: int
    read_cache_hits: str
    read_cache_overload: str
    write_cache_overload: str
    queued_io_jobs: int
    total_buffers_size: int
    total_queued_size: int


@declarative
class SyncMainData:
    """
    Sync results obtained from :meth:`.SyncAPI.maindata`.
    """

    rid: int
    full_update: bool = field(
        default=False,
    )

    torrents: Dict[str, SyncTorrentInfo] = field(
        default_factory=dict,
    )
    torrents_removed: List[str] = field(
        default_factory=list,
    )

    categories: Dict[str, SyncCategory] = field(
        default_factory=dict,
    )
    categories_removed: List[str] = field(
        default_factory=list,
    )

    tags: List[str] = field(
        default_factory=list,
    )
    tags_removed: List[str] = field(
        default_factory=list,
    )

    # trackers are new in 4.6.0
    trackers: Dict[str, List[str]] = field(
        default_factory=dict,
    )
    trackers_removed: List[str] = field(
        default_factory=list,
    )

    server_state: SyncServerState = field(
        default_factory=lambda: SyncServerState(),
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


@declarative
class SyncTorrentPeers:
    """
    See :meth:`.SyncAPI.torrent_peers`.
    """

    rid: int
    full_update: bool = field(default=False)
    # "show_flags" may be true, false or missing
    show_flags: Optional[bool] = field(default=None)
    peers: Dict[str, SyncPeer] = field(default_factory=dict)


@declarative
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

    connection_status: Union[str, ConnectionStatus] = field(
        convert=EnumConverter(ConnectionStatus),
    )


# RSS related
_RSS_SEPARATOR: Final = "\\"
_FEED_FOLDER_UNION = Union["RSSFeed", "RSSFolder"]


@declarative
class RSSArticle:
    """RSS article."""

    id: str
    title: str
    description: str
    date: datetime = field(
        convert=RFC2822DateTimeConverter(),
    )
    link: str
    torrentURL: str


@declarative
class RSSItem:
    """Base class of :class:`RSSFolder` and :class:`RSSFeed`"""


@declarative
class RSSFolder(RSSItem, Mapping[str, _FEED_FOLDER_UNION]):
    """
    RSSFolder is a container in hierarchical tree.

    .. code-block:: text

        folder
        |-- linux
        |-- news
        |   |-- local
        |   |-- world

    RSSFolder is a dict-like object that children :class:`RSSFeed` and :class:`RSSFolder` are
    accessed by their names: ``folder["linux"]``.
    The number of direct children is returned by ``len(folder)``
    while the names of them by ``folder.keys()``.

    Further children can be accessed by joining names with backslashes.
    The following lines are equivalent::

        folder["news"]["local"]
        folder[r"news\\local"]

    """

    _items: Mapping[str, _FEED_FOLDER_UNION]

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, path: str) -> _FEED_FOLDER_UNION:
        if _RSS_SEPARATOR not in path:
            return self._items[path]

        # use Any to pass typecheck
        items: Mapping[str, _FEED_FOLDER_UNION] = self._items
        parts = path.split(_RSS_SEPARATOR)
        end = len(parts) - 1
        for idx, name in enumerate(parts):
            if not name:
                raise KeyError(f"Empty segment at {idx}: {path!r}")

            try:
                result = items[name]
            except KeyError:
                raise KeyError(f"No item at {idx}: {path!r}")

            if idx == end:
                return result

            if not isinstance(result, RSSFolder):
                raise KeyError(f"Expect RSSFolder at {idx}: {path!r}")

            items = result._items

        raise AssertionError("unreachable")


@declarative
class RSSFeed(RSSItem):
    """
    RSS feed returned from :meth:`.RSSAPI.items`.

    Attributes ``url`` and ``uid``  are always available.

    The other attributes are available if ``with_data=True`` is passed to :meth:`.RSSAPI.items`.
    Otherwise, :class:`AttributeError` raises when accessed.

    Use :func:`hasattr` to check if doubted.
    """

    url: str
    uid: str

    # following attributes are available if with_data is set
    title: str
    lastBuildDate: str
    isLoading: bool
    hasError: bool
    articles: List[RSSArticle]  # entries are processed in RSSAPI.items()

    def __repr__(self) -> str:
        if hasattr(self, "title"):
            return f"<RSSFeed title={self.title!r} url={self.url!r}>"
        else:
            return f"<RSSFeed uid={self.uid!r} url={self.url!r}>"

    __str__ = __repr__


class RSSRule(TypedDict, total=False):
    """
    RSS rule configuration dict.

    Rule dict is returned from :meth:`.RSSAPI.rules`.
    It can be passed as argument to :meth:`.RSSAPI.set_rule`.
    """

    enabled: bool
    priority: int

    useRegex: bool
    mustContain: str
    mustNotContain: str
    episodeFilter: str
    affectedFeeds: List[str]
    savePath: str
    assignedCategory: str
    lastMatch: str
    ignoreDays: int
    addPaused: Optional[bool]
    torrentContentLayout: Optional[str]
    smartFilter: bool
    previouslyMatchedEpisodes: List[str]

    torrentParams: Dict[str, Any]  # TODO update the type when upstream work done


# Search related


@declarative
class SearchJobStart:
    """
    Result of :meth:`.SearchAPI.start`.
    """

    id: int


@declarative
class SearchJobStatus:
    """
    Search job status.
    """

    id: int
    status: Union[str, Literal["Running"], Literal["Stopped"]]
    total: int


@declarative
class SearchResultEntry:
    """Search result entry."""

    fileName: str
    fileUrl: str
    fileSize: str
    nbSeeders: int
    nbLeechers: int
    engineName: str  # API v2.11.1
    siteUrl: str
    descrLink: str
    pubDate: int  # API v2.11.1


@declarative
class SearchJobResults:
    """Search job results."""

    status: Union[str, Literal["Running"], Literal["Stopped"]]
    results: List[SearchResultEntry]
    total: int


@declarative
class SearchPluginCategory:
    """Category supported by plugin."""

    id: str
    category: str


@declarative
class SearchPlugin:
    """
    Search plugin information.
    """

    enabled: bool
    fullName: str
    name: str
    supportedCategories: Union[List[SearchPluginCategory], List[str]]
    """
    A list of supported categories.

    In qBittorrent 4.3.x and later, this attribute is a list of :class:`.SearchPluginCategory`;
    in earlier versions, a list of localized strings.
    """
    url: str
    version: str
