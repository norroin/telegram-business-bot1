import time

from aiogram import BaseMiddleware
from aiogram.types import Message

from database import execute
from utils import (
    check_sub,
    require_sub,
    register_user,
)

cooldowns = {}


class MainMiddleware(BaseMiddleware):

    async def __call__(self, handler, event: Message, data):

        if not isinstance(event, Message):
            return await handler(event, data)

        if not event.text:
            return await handler(event, data)

        if not event.text.startswith("/"):
            return await handler(event, data)

        bot = data["bot"]

        # Проверка подписки
        if not await check_sub(bot, -1002484763518, event):
            await require_sub(event)
            return

        # Регистрация пользователя
        await register_user(
            bot,
            5639087435,
            event
        )

        # Задержка
        user_id = event.from_user.id
        now = time.time()

        if user_id in cooldowns:
            if now - cooldowns[user_id] < 2:
                await event.answer(
                    "⏳ Подождите немного перед использованием следующей команды."
                )
                return

        cooldowns[user_id] = now

        # Логи команд
        execute(
            """
            INSERT INTO logs(user_id, action)
            VALUES (%s, %s)
            """,
            (
                user_id,
                f"Использовал {event.text.split()[0]}"
            )
        )

        return await handler(event, data)