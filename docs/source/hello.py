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
        await client.torrents.add(AddFormBuilder.with_client(client).include_url(url).build())

        await asyncio.sleep(10)  # wait a few seconds

        torrents = await client.torrents.info()
        for info in torrents:
            print(info)


if __name__ == "__main__":
    asyncio.run(main())
