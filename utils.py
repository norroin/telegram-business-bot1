from datetime import datetime

from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from database import execute


def get_role(user_id):
    row = execute(
        "SELECT role FROM roles WHERE user_id=%s",
        (user_id,)
    ).fetchone()

    if row:
        return row[0]

    return 0


def is_editor(user_id):
    return get_role(user_id) >= 1


def is_creator(user_id):
    return get_role(user_id) >= 2


def add_log(user_id, action):
    execute(
        """
        INSERT INTO logs(user_id, action)
        VALUES (%s, %s)
        """,
        (user_id, action)
    )


async def check_sub(bot, channel_id, message: Message):
    try:
        member = await bot.get_chat_member(
            channel_id,
            message.from_user.id
        )

        return member.status in (
            "member",
            "administrator",
            "creator"
        )
    except Exception:
        return False


async def require_sub(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Подписаться",
                    url="https://t.me/willyblackrussia"
                )
            ]
        ]
    )

    await message.answer(
        "❌ Для использования бота необходимо подписаться на канал.",
        reply_markup=kb
    )


async def register_user(bot, owner_id, message: Message):
    user = execute(
        "SELECT user_id FROM users WHERE user_id=%s",
        (message.from_user.id,)
    ).fetchone()

    if user:
        return

    execute(
        """
        INSERT INTO users(user_id, username, first_name, reg_date)
        VALUES (%s, %s, %s, %s)
        """,
        (
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
            datetime.now().strftime("%d.%m.%Y")
        )
    )

    await bot.send_message(
        owner_id,
        f"""🆕 Новый пользователь

👤 {message.from_user.full_name}
🆔 {message.from_user.id}
🔗 @{message.from_user.username or 'нет'}
"""
    )