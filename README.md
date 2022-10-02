# aioqbt

[![Documentation Status](https://readthedocs.org/projects/aioqbt/badge/?version=latest)](https://aioqbt.readthedocs.io/en/latest/?badge=latest)

API library for qBittorrent with asyncio.

It features async typed APIs and object-based results.

## Documentation

https://aioqbt.readthedocs.io/en/latest/

## Quick Start

Install with `pip`

```shell
$ pip install aioqbt
```

```python
import asyncio

from aioqbt.client import create_client
from aioqbt.api.types import InfoFilter


async def run():
    client = await create_client(
        "http://localhost:8080/api/v2/",
        username="admin",
        password="adminadmin",
    )

    async with client:
        # print client and API versions
        print(await client.app.version())  # v4.2.5
        print(await client.app.webapi_version())  # 2.5.1

        # print torrents in downloading
        for info in await client.torrents.info(filter=InfoFilter.DOWNLOADING):
            print(f"{info.added_on.isoformat()} added {info.name!r}")
            # 2022-09-10T17:59:00 added 'debian-11.5.0-amd64-netinst.iso'


if __name__ == '__main__':
    asyncio.run(run())
```

See [detailed usage on Read the Docs][1].

[1]: https://aioqbt.readthedocs.io/en/latest/usage.html