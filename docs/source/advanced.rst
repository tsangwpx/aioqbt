========
Advanced
========

Direct requests
---------------

:meth:`.APIClient.request` is a low-level interface to access API endpoints, and
returns a response object.

The use cases are not limited to accessing unsupported API endpoints,
or reducing type conversion overhead.

There are two helper methods in the client to deal with the response object.
They result in nice formats:

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
