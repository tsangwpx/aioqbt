============
Reference
============


Client
================

.. automodule:: aioqbt.client

.. autofunction:: create_client

.. autoclass:: APIClient()

    .. autoproperty:: app
    .. autoproperty:: auth
    .. autoproperty:: log
    .. autoproperty:: sync
    .. autoproperty:: torrents
    .. autoproperty:: transfer

    .. autoproperty:: client_version
    .. autoproperty:: api_version

    .. automethod:: is_closed
    .. automethod:: close

    .. automethod:: request
    .. automethod:: request_text
    .. automethod:: request_json

.. autoclass:: APIGroup()

APIs
================

.. automodule:: aioqbt.api

Torrents
----------------

.. autoclass:: TorrentsAPI()
    :members:
    :undoc-members:

.. autoclass:: AddFormBuilder()
    :members:
    :undoc-members:
    :exclude-members: client_version, api_version
    :member-order: bysource


App
----------------
.. autoclass:: AppAPI()
    :members:
    :undoc-members:


Auth
----------------
.. autoclass:: AuthAPI()
    :members:
    :undoc-members:


Log
----------------
.. autoclass:: LogAPI()
    :members:
    :undoc-members:


Sync
----------------
.. autoclass:: SyncAPI()
    :members:
    :undoc-members:


Transfer
----------------
.. autoclass:: TransferAPI()
    :members:
    :undoc-members:

API types
================

.. automodule:: aioqbt.api.types
    :synopsis: Constants and data structures

Constants
---------------

.. autoclass:: TorrentState()
    :members:
    :undoc-members:

.. autoclass:: InfoFilter()
    :members:
    :undoc-members:

.. autoclass:: PieceState()
    :members:
    :undoc-members:

.. autoclass:: TrackerStatus()
    :members:
    :undoc-members:

.. autoclass:: RatioLimits()
    :members:
    :undoc-members:

.. autoclass:: SeedingTimeLimits()
    :members:
    :undoc-members:

.. autoclass:: StopCondition()
    :members:
    :undoc-members:

.. autoclass:: ContentLayout()
    :members:
    :undoc-members:

.. autoclass:: FilePriority()
    :members:
    :undoc-members:

.. autoclass:: ConnectionStatus()
    :members:
    :undoc-members:

Data structures
----------------

.. autoclass:: BuildInfo()
    :members:
    :undoc-members:

.. autoclass:: Preferences()
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: NetworkInterface()
    :members:
    :undoc-members:

.. autoclass:: TorrentInfo()
    :members:
    :undoc-members:

.. autoclass:: TorrentProperties()
    :members:
    :undoc-members:

.. autoclass:: Tracker()
    :members:
    :undoc-members:

.. autoclass:: WebSeed()
    :members:
    :undoc-members:

.. autoclass:: FileEntry()
    :members:
    :undoc-members:

.. autoclass:: Category()
    :members:
    :undoc-members:

.. autoclass:: LogMessage()
    :members:
    :undoc-members:

.. autoclass:: LogPeer()
    :members:
    :undoc-members:

.. autoclass:: TransferInfo()
    :members:
    :undoc-members:

.. autoclass:: SyncMainData()
    :members:
    :undoc-members:

.. autoclass:: SyncTorrentInfo()
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: SyncCategory()
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: SyncServerState()
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: SyncTorrentPeers()
    :members:
    :undoc-members:

.. autoclass:: SyncPeer()
    :members:
    :undoc-members:
    :show-inheritance:



Utilities
================

bittorrent
--------------------------------

.. automodule:: aioqbt.bittorrent

.. data:: InfoHash
.. data:: InfoHashes
.. data:: InfoHashesOrAll

    Type hints related to info hash.

    * ``InfoHash`` represents an info hash (``str`` or ``bytes``).
    * ``InfoHashes`` is an iterable of ``InfoHash``.
    * ``InfoHashOrAll`` is an extension to ``InfoHashes``. It allow the string
      literal ``all``, which specifies all torrents in some API methods.

chrono
--------------------------------

.. automodule:: aioqbt.chrono

.. data:: Seconds
.. data:: Minutes

    Type hints (similar to ``int``) for time durations in specific units.

.. autoclass:: TimeUnit
    :members:
    :exclude-members:
        NANOSECONDS, MICROSECONDS, MILLISECONDS, SECONDS, MINUTES, HOURS, DAYS

    .. attribute:: NANOSECONDS
        :type: .TimeUnit

    .. attribute:: MICROSECONDS
        :type: .TimeUnit

    .. attribute:: MILLISECONDS
        :type: .TimeUnit

    .. attribute:: SECONDS
        :type: .TimeUnit

    .. attribute:: MINUTES
        :type: .TimeUnit

    .. attribute:: HOURS
        :type: .TimeUnit

    .. attribute:: DAYS
        :type: .TimeUnit

version
-------

.. automodule:: aioqbt.version

.. autoclass:: ClientVersion
    :members:

.. autoclass:: APIVersion
    :members:

Exceptions
==========

.. automodule:: aioqbt.exc

.. autoexception:: AQError()
    :show-inheritance:

.. autoexception:: MapperError()
    :show-inheritance:

.. autoexception:: VersionError()
    :show-inheritance:

.. autoexception:: APIError()
    :show-inheritance:
    :members:

.. autoexception:: LoginError()
    :show-inheritance:

.. autoexception:: AddTorrentError()
    :show-inheritance:

.. autoexception:: BadRequestError()
    :show-inheritance:

.. autoexception:: ForbiddenError()
    :show-inheritance:

.. autoexception:: NotFoundError()
    :show-inheritance:

.. autoexception:: ConflictError()
    :show-inheritance:

.. autoexception:: UnsupportedMediaTypeError()
    :show-inheritance:
