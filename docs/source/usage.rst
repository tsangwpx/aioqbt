.. _usage:

=====
Usage
=====

.. _installation:

Installation
------------

To use ``aioqbt``, first install it using pip:

.. code-block:: console

    $ pip install aioqbt

Creating clients
----------------

To create :class:`~aioqbt.client.APIClient`,
use :func:`~aioqbt.client.create_client()` with login credentials:

.. code-block:: python

    from aioqbt.client import create_client

    async def run():
        client = await create_client(
            "http://localhost:8080/api/v2/",
            username="admin",
            password="adminadmin",
        )

        async with client:
            print("Version", await client.app.version())
            print("API", await client.app.webapi_version())

    if __name__ == "__main__":
        asyncio.run(run())

Output:

.. code-block:: text

    Version v4.2.5
    API 2.5.1


Add & list torrents
-------------------

To add torrents,

    1. Obtain a builder with
       :meth:`AddFormBuilder.with_client(client) <.AddFormBuilder.with_client>`.
    2. Include torrent files and/or URLs.
    3. Build a form with :meth:`builder.build() <.AddFormBuilder.build>`, and pass it to
       :meth:`client.torrents.add() <.TorrentsAPI.add>`.

To get torrents, use :meth:`client.torrents.info() <.TorrentsAPI.info>` to obtain
a list of :class:`.TorrentInfo`.

Here is the code snippet:

.. code-block:: python

    from aioqbt.api import AddFormBuilder

    async def task(client: "aioqbt.client.APIClient"):
        # Add debian-11.5.0-amd64-netinst.iso by SHA-1 hash
        await client.torrents.add(
            AddFormBuilder.with_client(client)
            .include_url("d55be2cd263efa84aeb9495333a4fabc428a4250")
            .build()
        )

        # Print all torrent info
        for info in await client.torrents.info():
            print(info)

Method organizations
--------------------

WebUI APIs are organized into groups and methods.

For example, to access the ``torrents/addTrackers`` endpoint, use
:meth:`client.torrents.add_trackers() <.TorrentsAPI.add_trackers>`.

    * :attr:`client.torrents <.APIClient.torrents>` is an API group containing API
      methods with ``torrents/`` prefix.
    * ``addTrackers`` in camelCase is renamed to ``add_trackers()`` in snake_case.
    * Case conversion also applies to argument names.


Supported APIs
------------------

APIs are supported as needed.
Feature requests are welcome to discuss use-case details on :issue:`GitHub issues <>`.

The following table summarizes currently available APIs
and the corresponding attributes in :class:`.APIClient`.

.. list-table::
    :header-rows: 1

    * - API Group
      - Attribute
      - Reference
      - Notes
    * - :APIWiki:`Authentication <#authentication>`
      - :attr:`~.APIClient.auth`
      - :class:`~.AuthAPI`
      -
    * - :APIWiki:`Application <#application>`
      - :attr:`~.APIClient.app`
      - :class:`~.AppAPI`
      - ``preferences`` is not supported.
    * - :APIWiki:`Log <#log>`
      - :attr:`~.APIClient.log`
      - :class:`~.LogAPI`
      -
    * - :APIWiki:`Sync <#sync>`
      - :attr:`~.APIClient.sync`
      - :class:`~.SyncAPI`
      -
    * - :APIWiki:`Transfer info <#transfer-info>`
      - :attr:`~.APIClient.transfer`
      - :class:`~.TransferAPI`
      -
    * - :APIWiki:`Torrent management <#torrent-management>`
      - :attr:`~.APIClient.torrents`
      - :class:`~.TorrentsAPI`
      -
    * - :APIWiki:`RSS <#rss-experimental>`
      -
      -
      - Unsupported
    * - :APIWiki:`Search <#search>`
      -
      -
      - Unsupported
