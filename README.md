# aioqbt - API library for qBittorrent with asyncio
----------

### Example:

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
        print("Version", await client.app.version())
        print("API", await client.app.webapi_version())

        # print torrents in downloading
        for info in await client.torrents.info(filter=InfoFilter.DOWNLOADING):
            print(info)


if __name__ == '__main__':
    asyncio.run(run())
```
