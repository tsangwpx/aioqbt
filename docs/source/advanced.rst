========
Advanced
========

Direct requests
---------------

:class:`.APIClient` provides :meth:`.APIClient.request` to access API endpoints directly.

Both HTTP method (GET/POST) and endpoint are needed to specify.
URL parameters are passed as a dict to argument ``params``
while POST request data are passed to keyword argument ``data``.
They are then passed to the underlying :meth:`aiohttp.ClientSession.request`.

The returned result is :class:`aiohttp.ClientResponse` if succeeds.
See `the aiohttp documentation <https://docs.aiohttp.org/en/stable/client.html>`_ for details.
The method raises a subclass of :exc:`aioqbt.exc.APIError` if API error occurs, or
:exc:`aiohttp.ClientError` if connection error.

Convenient methods are included in the client to deal with :class:`~aiohttp.ClientResponse`
and result in nice formats:

    - :meth:`~.APIClient.request_json` returns JSON-decoded object.
    - :meth:`~.APIClient.request_text` returns ``str``.

The following code snippet prints a list of dicts of active torrents from ``torrents/info``  endpoint.

.. code-block:: python

    torrents = await client.request_json(
        "GET",
        "torrents/info",
        params={
            "filter": "active",
        },
    )
    pprint.pp(torrents)

.. code-block:: text

    [{'hash': '75439d5de343999ab377c617c2c647902956e282',
     'name': 'ubuntu-22.04.3-desktop-amd64.iso',
     'size': 5037662208,
     'state': 'uploading',
     # some keys are omitted
    }]
