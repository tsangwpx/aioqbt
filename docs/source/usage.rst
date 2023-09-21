.. _usage:

============
Basic usage
============

.. _installation:

Installation
------------

To use ``aioqbt``, first install it using pip:

.. code-block:: console

    $ pip install aioqbt

Create client
----------------

:class:`~aioqbt.client.APIClient` exposes Python interfaces to qBittorrent WebUI APIs
and maintains login session.
It is recommended to create them with :func:`~aioqbt.client.create_client()`
by supplying URL and login credential.
The interactions with the client are placed inside ``async with client`` block.

Let's create a client and inquire qBittorrent versions.

.. code-block:: python

    import asyncio

    from aioqbt.client import create_client

    async def main():
        client = await create_client(
            "http://localhost:8080/api/v2/",
            username="admin",
            password="adminadmin",
        )

        async with client:
            print("Version", await client.app.version())
            print("API", await client.app.webapi_version())

    asyncio.run(main())

Output:

.. code-block:: text

    Version v4.5.5
    API 2.8.19

Add torrents
-------------------

Here are the steps to add torrents:

    1. Create a builder with :meth:`AddFormBuilder.with_client(client) <.AddFormBuilder.with_client>`.
       It is a helper to build :class:`~aiohttp.FormData` for submission.
    2. Include torrent files :meth:`~.AddFormBuilder.include_file` or URLs :meth:`~.AddFormBuilder.include_url`.
    3. Call :meth:`builder.build() <.AddFormBuilder.build>`, and
       pass the result to :meth:`client.torrents.add() <.TorrentsAPI.add>`.

and the code follows:

.. code-block:: python

    from aioqbt.api import AddFormBuilder

    # Add ubuntu-22.04.3-desktop-amd64.iso
    url = "https://releases.ubuntu.com/22.04/ubuntu-22.04.3-desktop-amd64.iso.torrent"
    await client.torrents.add(
        AddFormBuilder.with_client(client)
        .include_url(url)
        .build()
    )


Get torrents
-------------------

To list the torrent we just added, use :meth:`client.torrents.info() <.TorrentsAPI.info>` to obtain
a list of :class:`.TorrentInfo`,
which encapsulates torrent info like name, state, and info hash::

    torrents = await client.torrents.info()
    for info in torrents:
        print(info)



Put things together:

.. code-block::

    import asyncio

    from aioqbt.api import AddFormBuilder
    from aioqbt.client import create_client


    async def main():
        client = await create_client(
            "http://localhost:8080/api/v2/",
            username="admin",
            password="adminadmin",
        )

        async with client:
            print("Version", await client.app.version())
            print("API", await client.app.webapi_version())

            # Add ubuntu-22.04.3-desktop-amd64.iso
            url = "https://releases.ubuntu.com/22.04/ubuntu-22.04.3-desktop-amd64.iso.torrent"
            await client.torrents.add(
                AddFormBuilder.with_client(client)
                .include_url(url)
                .build()
            )

            await asyncio.sleep(10) # wait a few seconds

            torrents = await client.torrents.info()
            for info in torrents:
                print(info)


    asyncio.run(main())


Output:

.. code-block:: text

    Version v4.5.5
    API 2.8.19
    <TorrentInfo 75439d5de343999ab377c617c2c647902956e282 downloading 'ubuntu-22.04.3-desktop-amd64.iso'>



API organization
--------------------

The qBittorrent WebUI APIs are organized into groups (auth, app, torrents, ...etc).
Each group can be accessed via :class:`.APIClient` attributes.
The qBittorrent Wiki provides a documentation as reference.

.. list-table::
    :header-rows: 1

    * - Client attribute
      - API Group
      - Wiki

    * - :attr:`~.APIClient.auth`
      - :class:`~.AuthAPI`
      - :APIWiki:`Authentication <#authentication>`

    * - :attr:`~.APIClient.app`
      - :class:`~.AppAPI`
      - :APIWiki:`Application <#application>`

    * - :attr:`~.APIClient.log`
      - :class:`~.LogAPI`
      - :APIWiki:`Log <#log>`

    * - :attr:`~.APIClient.sync`
      - :class:`~.SyncAPI`
      - :APIWiki:`Sync <#sync>`

    * - :attr:`~.APIClient.transfer`
      - :class:`~.TransferAPI`
      - :APIWiki:`Transfer info <#transfer-info>`

    * - :attr:`~.APIClient.torrents`
      - :class:`~.TorrentsAPI`
      - :APIWiki:`Torrent management <#torrent-management>`

For example, ``torrents/addTrackers`` endpoint under ``torrents`` group is represented
by :meth:`.TorrentsAPI.add_trackers`, which can be accessed
via client's ``torrents`` attribute:

.. code-block:: python

    await client.torrents.add_trackers(["http://example.com/tracker"])


.. note::

    In general, naming convention is applied in methods and parameters:
    `camelCase` is renamed to `snake_case`.