import asyncio
import aiohttp

async def main():
    connector = aiohttp.TCPConnector(family=2)  # AF_INET = только IPv4

    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get("https://api.telegram.org") as resp:
            print(resp.status)
            print(await resp.text())

asyncio.run(main())