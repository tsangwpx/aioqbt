# aioqbt

[![Documentation Status](https://readthedocs.org/projects/aioqbt/badge/?version=latest)](https://aioqbt.readthedocs.io/en/latest/?badge=latest)

Python library for qBittorrent WebAPI with asyncio.

Features:
* Async typed interfaces.
* Complete qBittorrent WebAPI.
* Tested with qBittorrent v4.1.5 to v5.0.2 on Debian/Ubuntu.

## Documentation

https://aioqbt.readthedocs.io/en/latest/

## Quick Start

Install with `pip`

```shell
$ pip install aioqbt
```

```python
import asyncio

from aioqbt.api import InfoFilter
from aioqbt.client import create_client


async def main():
    client = await create_client(
        "http://localhost:8080/api/v2/",
        username="admin",
        password="adminadmin",
    )

    async with client:
        # print client and API versions
        print(await client.app.version())  # v4.6.1
        print(await client.app.webapi_version())  # 2.9.3

        # print torrents in downloading
        for info in await client.torrents.info(filter=InfoFilter.DOWNLOADING):
            print(f"{info.added_on.isoformat()} added {info.name!r}")
            # 2023-11-06T17:59:00 added 'ubuntu-22.04.3-desktop-amd64.iso'


if __name__ == '__main__':
    asyncio.run(main())
```

See [detailed usage on Read the Docs][1].

[1]: https://aioqbt.readthedocs.io/en/latest/usage.html