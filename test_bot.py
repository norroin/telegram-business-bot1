import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot

load_dotenv()

async def main():
    token = os.getenv("TOKEN")
    print("TOKEN:", token[:10] + "..." if token else "НЕ НАЙДЕН")

    bot = Bot(token)

    me = await bot.get_me()

    print(me)

    await bot.session.close()

asyncio.run(main())