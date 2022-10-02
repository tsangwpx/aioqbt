========
Advanced
========

Direct requests
---------------

To initiate HTTP request directly, use :meth:`.APIClient.request` method to obtain
:class:`~aiohttp.ClientResponse`. Optional arguments ``params`` and ``data`` are passed
to :meth:`ClientSession.request() <aiohttp.ClientSession.request>` in aiohttp library.

Variant methods are provided to extract result in specific format:

    - :meth:`~.APIClient.request_json` returns JSON-decoded object.
    - :meth:`~.APIClient.request_text` returns ``str``.

The following code snippet requests a torrent list directly from ``torrents/info``
endpoint and results in a list of ``dict``.

.. code-block:: python

    torrents = await client.request_json("GET", "torrents/info")
