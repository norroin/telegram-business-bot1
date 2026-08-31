import os
import asyncio
import init_db
import cloudinary
import cloudinary.uploader
import re

from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand
)

from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from database import cur, db, execute 

from utils import (
    check_sub,
    require_sub,
    register_user,
    get_role,
    is_editor,
    is_creator,
    add_log,
)

from middlewares import MainMiddleware

from datetime import datetime, timedelta

waiting_upload = {}

waiting_reports = {}

active_reports = {}

waiting_rep_answer = {}

TOKEN = os.getenv("TOKEN")
ADMINS = [5639087435]

bot = Bot(TOKEN) 
dp = Dispatcher()

dp.message.middleware(MainMiddleware())

waiting_zbt = set()

UPLOAD_WAIT = set()

CHANNEL_ID = -1002484763518
OWNER_ID = 5639087435

cloudinary.config(
    cloud_name="p606sotg",
    api_key="398575342634263",
    api_secret="5nwNll0tGlmFTnkYY5QyENPsv-8",
    secure=True
)


class AddBusiness(StatesGroup):
    id = State()
    name = State()
    owner = State()
    category = State()
    location = State()

class ChangeOwner(StatesGroup):
    business_id = State()
    owner = State()

class ChangeLocation(StatesGroup):
    business_id = State()
    location = State()

class UploadPhoto(StatesGroup):
    business_id = State()
    photo = State()


class ChangePhotoCmd(StatesGroup):
    business_id = State()
    photo = State()

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

@dp.message(Command("start"))
async def start(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await register_user(message)
        return

    await register_user(bot, OWNER_ID, message)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏢 Бизнесы",
                    callback_data="biz"
                ),
                InlineKeyboardButton(
                    text="📂 Категории",
                    callback_data="categories"
                ),
                InlineKeyboardButton(
                    text="ℹ️ Помощь",
                    callback_data="help"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📥 Скачать ЗБТ",
                    callback_data="zbt_info"
                ),
                InlineKeyboardButton(
                    text="👮 Админы",
                    callback_data="admins_info"
                ),
                InlineKeyboardButton(
                    text="📝 Написать жалобу",
                    callback_data="report_info"
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ Информация",
                    callback_data="start_info"
                ),
                InlineKeyboardButton(
                    text="⚔️ Битва семей",
                    callback_data="start_bs"
                )
            ]
        ]
    )

    await message.answer(
        f"👋 **Привет, {message.from_user.first_name}!**\n"
        "**Я BOT BRYANSK — бот-помощник по игре Black Russia сервера BRYANSK[66].**\n\n"
        "**Выбери раздел ниже 👇**",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.message(Command("business"))
async def business(message: Message):
    
    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        await message.answer(
            "Пример:\n/business 15\nили\n/business Автосервис"
        )
        return

    search = args[1]

    # Поиск по ID
    if search.isdigit():
        row = execute(
            """
            SELECT name, owner, location, photo_id, category
            FROM businesses
            WHERE id=%s
            """,
            (search,)
        ).fetchone()

        if not row:
            await message.answer("Бизнес не найден.")
            return

        name, owner, location, photo_id, category = row

        text = (
            f"🏢 Полное название: {name}\n\n"
            f"📂 Категория: {category or 'Не указана'}\n\n"
            f"👤 Владелец: {owner}\n\n"
            f"📍 Местоположение:\n{location}"
        )

        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)

        return

    # Поиск по названию
    name_rows = execute(
        """
        SELECT id, name
        FROM businesses
        WHERE name LIKE %s
        ORDER BY name
        """,
        (f"%{search}%",)
    ).fetchall()

    if name_rows:
        text = "🔎 Найдено по названию:\n\n"

        for business_id, name in name_rows:
            text += f"🆔 {business_id} | {name}\n"

        await message.answer(text)
        return

    # Поиск по категории
    category_rows = execute(
        """
        SELECT id, name
        FROM businesses
        WHERE category=%s
        ORDER BY name
        """,
        (search,)
    ).fetchall()

    if rows:
        text = f"📂 Категория: {search}\n\n"

        for business_id, name in rows:
            text += f"🆔 {business_id} | {name}\n"

        await message.answer(text)
        return

    # Ничего не найдено
    await message.answer("Бизнес или категория не найдены.")

@dp.message(Command("bizlist"))
async def bizlist(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    rows = execute(
        "SELECT id, name FROM businesses ORDER BY id"
    ).fetchall()

    if not rows:
        await message.answer("Список бизнесов пуст.")
        return

    text = "📋 Список бизнесов\n\n"

    for business_id, name in rows:
        text += f"{business_id} - {name}\n"

    await message.answer(text)

# ============================================================
# КАТЕГОРИИ
# ============================================================

CAR_CATEGORIES = [
    "Низкий класс",
    "Средний класс",
    "Высокий класс",
    "Грузовой класс",
    "Мотоциклы",
    "Яхты",
    "Уникальный класс",
    "Организации",
    "Рабочий класс",
    "Прицепы"
]


# ============================================================
# ЭМОДЗИ КАТЕГОРИЙ
# ============================================================

CATEGORY_EMOJIS = {
    "Низкий класс": "🚗",
    "Средний класс": "🚘",
    "Высокий класс": "🏎",
    "Грузовой класс": "🚛",
    "Мотоциклы": "🏍",
    "Яхты": "🛥",
    "Уникальный класс": "⭐",
    "Организации": "🏢",
    "Рабочий класс": "🚒",
    "Прицепы": "🚚"
}


# ============================================================
# ЭМОДЗИ ЗАГОЛОВКОВ
# ============================================================

CATEGORY_TITLES = {
    "Низкий класс": "🚗 Транспорт низкого автосалона",
    "Средний класс": "🚘 Транспорт среднего автосалона",
    "Высокий класс": "🏎 Транспорт высокого автосалона",
    "Грузовой класс": "🚛 Транспорт грузового автосалона",
    "Мотоциклы": "🏍 Транспорт мотосалона",
    "Яхты": "🛥 Транспорт салона яхт",
    "Уникальный класс": "⭐ Уникальный транспорт",
    "Организации": "🏢 Уникальный транспорт организаций",
    "Рабочий класс": "🚒 Рабочий транспорт",
    "Прицепы": "🚚 Прицепы"
}


# ============================================================
# 20 МАШИН НА СТРАНИЦУ
# ============================================================

CARS_PER_PAGE = 20


# ============================================================
# ОПРЕДЕЛЕНИЕ КАТЕГОРИИ ПРИ ИМПОРТЕ
# ============================================================

def detect_car_category(line: str):

    text = line.replace("*", "").strip().lower()

    if "низкого автосалона" in text:
        return "Низкий класс"

    if "среднего автосалона" in text:
        return "Средний класс"

    if "высокого автосалона" in text:
        return "Высокий класс"

    if "грузового автосалона" in text:
        return "Грузовой класс"

    if "мотосалона" in text:
        return "Мотоциклы"

    if "салона яхт" in text:
        return "Яхты"

    # Уникальный транспорт
    if "уникальный транспорт организаций" in text:
        return "Организации"

    if "уникальный транспорт" in text:
        return "Уникальный класс"

    # Рабочий транспорт
    if "рабочий транспорт" in text:
        return "Рабочий класс"

    # Прицепы
    if "прицепы" in text:
        return "Прицепы"

    return None


# ============================================================
# /importcars
# ============================================================

@dp.message(Command("importcars"))
async def importcars(message: Message):

    if message.from_user.id not in ADMINS and not is_creator(message.from_user.id):
        return

    text = re.sub(
        r"^/importcars(?:@\w+)?\s*",
        "",
        message.text,
        count=1,
        flags=re.IGNORECASE
    )

    if not text.strip():

        await message.answer(
            "❌ После /importcars нужно вставить список транспорта."
        )

        return

    current_category = None

    added = 0
    updated = 0
    skipped = 0

    for raw_line in text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        # Убираем *** в начале и конце
        clean_line = line.strip("*").strip()

        if not clean_line:
            continue

        # ----------------------------------------------------
        # ПРОВЕРЯЕМ ЗАГОЛОВОК
        # ----------------------------------------------------

        detected_category = detect_car_category(clean_line)

        if detected_category:

            current_category = detected_category

            continue

        # ----------------------------------------------------
        # ЕСЛИ КАТЕГОРИЯ НЕ ОПРЕДЕЛЕНА
        # ----------------------------------------------------

        if current_category is None:

            skipped += 1

            continue

        # ----------------------------------------------------
        # ИЩЕМ ID
        #
        # Поддерживает:
        #
        # 555 - ZAZ 968
        #
        # 2552 Toyota Supra A80
        # ----------------------------------------------------

        match = re.match(
            r"^(\d+)\s*(?:-\s*)?(.+?)$",
            clean_line
        )

        if not match:

            skipped += 1

            continue

        game_id = int(match.group(1))

        full_name = match.group(2).strip()

        if not full_name:

            skipped += 1

            continue

        full_name = full_name.replace("*", "").strip()

        organization = None

        # ----------------------------------------------------
        # ОРГАНИЗАЦИИ
        #
        # Gazon Next | Армия
        # ----------------------------------------------------

        if "|" in full_name:

            name_part, organization_part = full_name.split(
                "|",
                1
            )

            full_name = name_part.strip()

            organization = organization_part.strip()

        # ----------------------------------------------------
        # ПРОВЕРЯЕМ СУЩЕСТВУЮЩУЮ МАШИНУ
        #
        # Проверяем game_id + category.
        #
        # Поэтому один ID может быть:
        #
        # 403 - Renault Premium
        # Грузовой класс
        #
        # и одновременно:
        #
        # 403 - Renault Premium
        # Рабочий класс
        # ----------------------------------------------------

        existing = execute(
            """
            SELECT game_id
            FROM cars
            WHERE game_id=%s
            AND category=%s
            LIMIT 1
            """,
            (
                game_id,
                current_category
            )
        ).fetchone()

        # ----------------------------------------------------
        # ОБНОВЛЕНИЕ
        # ----------------------------------------------------

        if existing:

            execute(
                """
                UPDATE cars
                SET name=%s,
                    organization=%s
                WHERE game_id=%s
                AND category=%s
                """,
                (
                    full_name,
                    organization,
                    game_id,
                    current_category
                )
            )

            updated += 1

        # ----------------------------------------------------
        # ДОБАВЛЕНИЕ
        # ----------------------------------------------------

        else:

            execute(
                """
                INSERT INTO cars
                (
                    game_id,
                    name,
                    category,
                    organization
                )
                VALUES(%s,%s,%s,%s)
                """,
                (
                    game_id,
                    full_name,
                    current_category,
                    organization
                )
            )

            added += 1

    await message.answer(
        "✅ <b>Импорт транспорта завершён!</b>\n\n"
        f"➕ Добавлено: <b>{added}</b>\n"
        f"🔄 Обновлено: <b>{updated}</b>\n"
        f"⚠️ Пропущено: <b>{skipped}</b>",
        parse_mode="HTML"
    )


# ============================================================
# ГЛАВНОЕ МЕНЮ /carlist
# ============================================================

def car_categories_keyboard():

    buttons = []

    for i in range(0, len(CAR_CATEGORIES), 2):

        row = []

        for category in CAR_CATEGORIES[i:i + 2]:

            emoji = CATEGORY_EMOJIS.get(
                category,
                "🚗"
            )

            row.append(
                InlineKeyboardButton(
                    text=f"{emoji} {category}",
                    callback_data=f"carcat:{category}"
                )
            )

        buttons.append(row)

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# ============================================================
# КНОПКИ СПИСКА МАШИН
# ============================================================

def cars_keyboard(
    category: str,
    page: int,
    total_pages: int
):

    buttons = []

    # --------------------------------------------------------
    # Навигация
    # --------------------------------------------------------

    navigation = []

    if page > 1:

        navigation.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"carpage:{category}:{page - 1}"
            )
        )

    navigation.append(
        InlineKeyboardButton(
            text=f"📄 {page}/{total_pages}",
            callback_data="car_noop"
        )
    )

    if page < total_pages:

        navigation.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"carpage:{category}:{page + 1}"
            )
        )

    buttons.append(navigation)

    # --------------------------------------------------------
    # Назад
    # --------------------------------------------------------

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="car_back"
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# ============================================================
# ПОКАЗ КАТЕГОРИИ
# ============================================================

async def show_car_category(
    message: Message,
    category: str,
    page: int = 1
):

    # --------------------------------------------------------
    # Сколько всего машин
    # --------------------------------------------------------

    count_result = execute(
        """
        SELECT COUNT(*)
        FROM cars
        WHERE category=%s
        """,
        (category,)
    ).fetchone()

    total = count_result[0] if count_result else 0

    # --------------------------------------------------------
    # Нет машин
    # --------------------------------------------------------

    if total == 0:

        title = CATEGORY_TITLES.get(
            category,
            category
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="car_back"
                    )
                ]
            ]
        )

        await message.edit_text(
            f"<b>{title}</b>\n\n"
            "🚫 В этой категории пока нет транспорта.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        return

    # --------------------------------------------------------
    # Количество страниц
    # --------------------------------------------------------

    total_pages = (
        total + CARS_PER_PAGE - 1
    ) // CARS_PER_PAGE

    if page < 1:
        page = 1

    if page > total_pages:
        page = total_pages

    offset = (
        page - 1
    ) * CARS_PER_PAGE

    # --------------------------------------------------------
    # Получаем машины
    # --------------------------------------------------------

    rows = execute(
        """
        SELECT game_id, name, organization
        FROM cars
        WHERE category=%s
        ORDER BY game_id
        LIMIT %s OFFSET %s
        """,
        (
            category,
            CARS_PER_PAGE,
            offset
        )
    ).fetchall()

    title = CATEGORY_TITLES.get(
        category,
        category
    )

    text = (
        f"<b>{title}</b>\n"
        f"📄 Страница {page}/{total_pages}\n\n"
    )

    # --------------------------------------------------------
    # Список
    # --------------------------------------------------------

    for game_id, name, organization in rows:

        text += (
            f"🆔 <code>{game_id}</code> — "
            f"<b>{name}</b>"
        )

        if organization:

            text += (
                f" | 🏢 {organization}"
            )

        text += "\n"

    keyboard = cars_keyboard(
        category,
        page,
        total_pages
    )

    await message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ============================================================
# КОМАНДА /carlist
# ============================================================

@dp.message(Command("carlist"))
async def carlist(message: Message):

    await message.answer(
        "🚗 <b>Каталог транспорта</b>\n\n"
        "Выберите нужную категорию:",
        reply_markup=car_categories_keyboard(),
        parse_mode="HTML"
    )


# ============================================================
# ВЫБОР КАТЕГОРИИ
# ============================================================

@dp.callback_query(
    F.data.startswith("carcat:")
)
async def car_category_callback(
    callback: CallbackQuery
):

    category = callback.data.split(
        ":",
        1
    )[1]

    if category not in CAR_CATEGORIES:

        await callback.answer(
            "Категория не найдена."
        )

        return

    await show_car_category(
        callback.message,
        category,
        1
    )

    await callback.answer()


# ============================================================
# ПЕРЕКЛЮЧЕНИЕ СТРАНИЦ
# ============================================================

@dp.callback_query(
    F.data.startswith("carpage:")
)
async def car_page_callback(
    callback: CallbackQuery
):

    parts = callback.data.split(":")

    if len(parts) != 3:

        await callback.answer()

        return

    category = parts[1]

    try:

        page = int(parts[2])

    except ValueError:

        await callback.answer()

        return

    if category not in CAR_CATEGORIES:

        await callback.answer(
            "Категория не найдена."
        )

        return

    await show_car_category(
        callback.message,
        category,
        page
    )

    await callback.answer()


# ============================================================
# НАЗАД К КАТЕГОРИЯМ
# ============================================================

@dp.callback_query(
    F.data == "car_back"
)
async def car_back_callback(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "🚗 <b>Каталог транспорта</b>\n\n"
        "Выберите нужную категорию:",
        reply_markup=car_categories_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# ============================================================
# КНОПКА СТРАНИЦЫ 1/3 И Т.П.
# ============================================================

@dp.callback_query(
    F.data == "car_noop"
)
async def car_noop(
    callback: CallbackQuery
):

    await callback.answer()

# =========================================================
# ГЛАВНОЕ МЕНЮ INFO
# =========================================================

def info_main_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎨 Палитра цветов",
                    callback_data="info:colors"
                ),
                InlineKeyboardButton(
                    text="📋 КТС / ЗКТС",
                    callback_data="info:kts"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👮 Список ГА",
                    callback_data="info:ga"
                ),
                InlineKeyboardButton(
                    text="🤖 Список команд",
                    callback_data="info:commands"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📜 Правила",
                    callback_data="info:rules"
                ),
                InlineKeyboardButton(
                    text="🛠 Тех отдел",
                    callback_data="info:tech"
                )
            ]
        ]
    )


# =========================================================
# КОМАНДА /INFO
# =========================================================

@dp.message(Command("info"))
async def info(message: Message):

    await message.answer(
        "ℹ️ <b>Полезная информация</b>\n\n"
        "Здесь собрана полезная информация для новичков "
        "и игроков сервера.\n\n"
        "Выберите нужный раздел 👇",
        reply_markup=info_main_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# ОБРАБОТКА КНОПОК INFO
# =========================================================

@dp.callback_query(F.data.startswith("info:"))
async def info_callback(callback: CallbackQuery):

    section = callback.data.split(":")[1]


    # =====================================================
    # ПАЛИТРА
    # =====================================================

    if section == "colors":

        text = (
            "🎨 <b>Палитра цветов</b>\n\n"
            "Здесь вы можете ознакомиться с палитрой "
            "цветов, используемых в игре.\n\n"
            "Нажмите кнопку ниже, чтобы открыть палитру."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎨 Открыть палитру",
                        url="https://forum.blackrussia.online/threads/black-russia-Палитра-цветов.10019830/"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="info:main"
                    )
                ]
            ]
        )


    # =====================================================
    # КТС / ЗКТС
    # =====================================================

    elif section == "kts":

        text = (
            "📋 <b>Список КТС / ЗКТС</b>\n\n"
            "Здесь находится актуальный список КТС,КТС и история тех.отдела.\n\n"
            "Нажмите кнопку ниже, чтобы открыть список."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Открыть список",
                        url="https://forum.blackrussia.online/threads/black-russia-История-руководства-технических-специалистов-Список-кураторов-зам-кураторов-тех-специалистов-Тех-специалисты-2020-2021-годов.11074252/"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="info:main"
                    )
                ]
            ]
        )


    # =====================================================
    # ГА
    # =====================================================

    elif section == "ga":

        text = (
            "👮 <b>Список ГА</b>\n\n"
            "Здесь находится актуальный список ГА и адм.отдела\n\n"
            "Нажмите кнопку ниже, чтобы открыть список."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👮 Открыть список ГА",
                        url="https://forum.blackrussia.online/threads/black-russia-История-ГА-Список-Главных-Администраторов-всех-серверов-рук-администрации-СА-ЗСА-Официальные-ресурсы-vk-forum-всех-серверов.11062508/"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="info:main"
                    )
                ]
            ]
        )


    # =====================================================
    # КОМАНДЫ
    # =====================================================

    elif section == "commands":

        text = (
            "🤖 <b>Список команд</b>\n\n"
            "Здесь находится список доступных команд BLACK RUSSIA.\n\n"
            "Нажмите кнопку ниже, чтобы посмотреть команды."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🤖 Открыть список команд",
                        url="https://forum.blackrussia.online/threads/black-russia-Актуальный-список-команд-сервера.11069991/"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="info:main"
                    )
                ]
            ]
        )


    # =====================================================
    # ПРАВИЛА
    # =====================================================

    elif section == "rules":

        text = (
            "📜 <b>Правила</b>\n\n"
            "Здесь находятся актуальные правила BLACK RUSSIA.\n\n"
            "Перед началом игры рекомендуется ознакомиться "
            "со всеми правилами."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📜 Открыть правила",
                        url="https://forum.blackrussia.online/forums/Общие-правила-серверов.51/"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="info:main"
                    )
                ]
            ]
        )


    # =====================================================
    # ТЕХ ОТДЕЛ
    # =====================================================

    elif section == "tech":

        text = (
            "🛠 <b>Технический отдел</b>\n\n"
            "Здесь находится технического отдела.\n\n"
            "Нажмите кнопку ниже, чтобы перейти к материалам."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛠 Открыть тех отдел",
                        url="https://forum.blackrussia.online/forums/Технический-раздел.22/"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="info:main"
                    )
                ]
            ]
        )


    # =====================================================
    # НАЗАД
    # =====================================================

    elif section == "main":

        await callback.message.edit_text(
            "ℹ️ <b>Полезная информация</b>\n\n"
            "Здесь собрана полезная информация для новичков "
            "и игроков сервера.\n\n"
            "Выберите нужный раздел 👇",
            reply_markup=info_main_keyboard(),
            parse_mode="HTML"
        )

        await callback.answer()
        return


    else:
        await callback.answer()
        return


    # =====================================================
    # ИЗМЕНЯЕМ ТО ЖЕ САМОЕ СООБЩЕНИЕ
    # =====================================================

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await callback.answer()

@dp.message(Command("admintab"))
async def admintab(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    if get_role(message.from_user.id) < 2:
        await message.answer("❌ Недостаточно прав.")
        return

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить бизнес")],
            [KeyboardButton(text="👤 Изменить владельца")],
            [KeyboardButton(text="📍 Изменить адрес")],
            [KeyboardButton(text="📷 Добавить фото")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "Админ-панель",
        reply_markup=kb
    )

@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)
    
    current = await state.get_state()

    if current:
        await state.clear()
        await message.answer("Текущее действие отменено.")
    else:
        await message.answer("Нет активного действия.")

@dp.message(F.text == "➕ Добавить бизнес")
async def add_start(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return
    
    if message.from_user.id not in ADMINS:
        return

    await state.set_state(AddBusiness.id)
    await message.answer("Введите ID бизнеса")


@dp.message(AddBusiness.name)
async def add_name(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await state.update_data(name=message.text)
    await state.set_state(AddBusiness.owner)
    await message.answer("Введите владельца")

@dp.message(AddBusiness.id)
async def add_id(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    if message.text and message.text.startswith("/"):
        return

    try:
        business_id = int(message.text)
    except ValueError:
        await message.answer(
            "ID бизнеса должен быть числом.\nПример: 1"
        )
        return

    if execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    ).fetchone():
        await message.answer(
        "Бизнес с таким ID уже существует."
        )
        return

    await state.update_data(id=business_id)
    await state.set_state(AddBusiness.name)

    await message.answer(
        "Введите название бизнеса"
    )

@dp.message(AddBusiness.owner)
async def add_owner(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return
   
    await state.update_data(owner=message.text)
    await state.set_state(AddBusiness.category)
    await message.answer("Введите категорию")


@dp.message(AddBusiness.category)
async def add_category(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    await state.update_data(category=message.text)
    await state.set_state(AddBusiness.location)
    await message.answer("Введите адрес")


@dp.message(AddBusiness.location)
async def add_location(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    data = await state.get_data()

    execute(
        """
        INSERT INTO businesses
        (id, name, owner, category, location)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            data["id"],
            data["name"],
            data["owner"],
            data["category"],
            message.text
        )
    )

    

    await state.clear()
    await message.answer("Бизнес добавлен.")

@dp.message(F.text == "👤 Изменить владельца")
async def owner_start(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    await state.set_state(ChangeOwner.business_id)
    await message.answer("Введите ID бизнеса")

@dp.message(ChangeOwner.business_id)
async def owner_bid(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    await state.update_data(id=message.text)
    await state.set_state(ChangeOwner.owner)
    await message.answer("Введите нового владельца")

@dp.message(ChangeOwner.owner)
async def owner_save(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    data = await state.get_data()

    execute(
        "UPDATE businesses SET owner=%s WHERE id=%s",
        (message.text, data["id"])
    )
    

    await state.clear()
    await message.answer("Владелец изменён.")

@dp.message(F.text == "📍 Изменить адрес")
async def location_start(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    await state.set_state(ChangeLocation.business_id)
    await message.answer("Введите ID бизнеса")

@dp.message(ChangeLocation.business_id)
async def location_bid(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    await state.update_data(id=message.text)
    await state.set_state(ChangeLocation.location)
    await message.answer("Введите новый адрес")

@dp.message(ChangeLocation.location)
async def location_save(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    data = await state.get_data()

    execute(
        "UPDATE businesses SET location=%s WHERE id=%s",
        (message.text, data["id"])
    )
    

    await state.clear()
    await message.answer("Адрес обновлён.")

@dp.message(F.text == "📷 Добавить фото")
async def photo_start(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    await state.set_state(UploadPhoto.business_id)
    await message.answer("Введите ID бизнеса")

@dp.message(UploadPhoto.business_id)
async def photo_bid(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    await state.update_data(id=message.text)
    await state.set_state(UploadPhoto.photo)
    await message.answer("Отправьте фотографию")

@dp.message(UploadPhoto.photo, F.photo)
async def photo_save(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    data = await state.get_data()

    photo_id = message.photo[-1].file_id

    execute(
        "UPDATE businesses SET photo_id=%s WHERE id=%s",
        (photo_id, data["id"])
    )
    

    await state.clear()
    await message.answer("Фото сохранено.")


@dp.message(Command("setrole"))
async def set_role(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    if message.from_user.id not in ADMINS:
        return

    args = message.text.split()

    if len(args) != 3:
        await message.answer(
            "Пример:\n"
            "/setrole 123456789 1\n\n"
            "Роли:\n"
            "0 — Пользователь\n"
            "1 — Редактор\n"
            "2 — Создатель"
        )
        return

    try:
        user_id = int(args[1])
        role = int(args[2])
    except ValueError:
        await message.answer(
            "❌ ID пользователя и роль должны быть числами.\n\n"
            "Пример:\n"
            "/setrole 123456789 1"
        )
        return

    if role not in [0, 1, 2]:
        await message.answer(
            "❌ Неверная роль.\n\n"
            "0 — Пользователь\n"
            "1 — Редактор\n"
            "2 — Создатель"
        )
        return

    execute(
        """
        INSERT INTO roles (user_id, role)
        VALUES (%s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET role = EXCLUDED.role
        """,
        (user_id, role)
    )

    await message.answer(
        f"✅ Роль {role} выдана пользователю {user_id}."
    )

@dp.message(Command("cbiz"))
async def cbiz(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    if not is_editor(message.from_user.id):
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "Пример:\n/cbiz 15 Автосервис"
        )
        return

    business_id = args[1]
    category = args[2]

    execute(
        "UPDATE businesses SET category=%s WHERE id=%s",
        (category, business_id)
    )
    

    await message.answer("Категория сохранена.")

@dp.message(Command("delcbiz"))
async def delcbiz(message: Message):
    
    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    if not is_editor(message.from_user.id):
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "Пример:\n/delcbiz 15"
        )
        return

        execute(
        "UPDATE businesses SET category=NULL WHERE id=%s",
        (args[1],)
    )

        

    await message.answer(
        "Категория удалена."
    )

@dp.message(Command("nbiz"))
async def nbiz(message: Message):
    
    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    if not is_creator(message.from_user.id):
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "Пример:\n/nbiz 15 Новое название"
        )
        return

    business_id = args[1]
    new_name = args[2]

    if not execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    ).fetchone():
        await message.answer("Бизнес не найден.")
        return

    execute(
        "UPDATE businesses SET name=%s WHERE id=%s",
        (new_name, business_id)
    )

    

    await message.answer("Название бизнеса изменено.")

@dp.message(Command("lbiz"))
async def lbiz(message: Message):
    
    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    if not is_creator(message.from_user.id):
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "Пример:\n/lbiz 15 Новый адрес"
        )
        return

    business_id = args[1]
    new_location = args[2]

    if not execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    ).fetchone():
        await message.answer("Бизнес не найден.")
        return

    execute(
        "UPDATE businesses SET location=%s WHERE id=%s",
        (new_location, business_id)
    ) 


    await message.answer(
        "Адрес бизнеса изменён."
    )

@dp.message(Command("delbiz"))
async def delbiz(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    if not is_creator(message.from_user.id):
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "Пример:\n/delbiz 15"
        )
        return

    business_id = args[1]

    if not execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    ).fetchone():
        await message.answer("Бизнес не найден.")
        return

    execute(
        "DELETE FROM businesses WHERE id=%s",
        (business_id,)
    )


    add_log(
        message.from_user.id,
        f"Удалил бизнес {business_id}"
    )

    await message.answer(
        "Бизнес удалён."
    )
    
@dp.message(Command("vbiz"))
async def vbiz(message: Message):
    
    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    if not is_editor(message.from_user.id):
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "Пример:\n/vbiz 15 Иван Петров"
        )
        return

    business_id = args[1]
    new_owner = args[2]

    if not execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    ).fetchone():
        await message.answer("Бизнес не найден.")
        return

    execute(
        "UPDATE businesses SET owner=%s WHERE id=%s",
        (new_owner, business_id)
    )


    add_log(
    message.from_user.id,
    f"Изменил владельца бизнеса {business_id}"
    )

    await message.answer(
        "Владелец бизнеса изменён."
    )

@dp.message(Command("fbiz"))
async def fbiz(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    if not is_editor(message.from_user.id):
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "Пример:\n/fbiz 15"
        )
        return

    business_id = args[1]

    if not execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    ).fetchone():
        await message.answer(
        "Бизнес не найден."
        )
        return

    await state.update_data(id=business_id)

    await state.set_state(ChangePhotoCmd.photo)

    await message.answer(
        "Отправьте новую фотографию."
    )

@dp.message(ChangePhotoCmd.photo, F.photo)
async def fbiz_save(message: Message, state: FSMContext):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    data = await state.get_data()

    photo_id = message.photo[-1].file_id

    execute(
        "UPDATE businesses SET photo_id=%s WHERE id=%s",
        (photo_id, data["id"])
    )



    await state.clear()

    await message.answer(
        "Фотография бизнеса обновлена."
    )

@dp.message(Command("categories"))
async def categories(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)
    
    rows = execute(
        """
        SELECT DISTINCT category
        FROM businesses
        WHERE category IS NOT NULL
        AND category != ''
        ORDER BY category
        """
    ).fetchall()

    if not rows:
        await message.answer("Категории отсутствуют.")
        return

    text = "📂 Категории\n\n"

    for (category,) in rows:
        text += f"• {category}\n"

    await message.answer(text)

@dp.message(Command("support"))
async def support(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    role = get_role(message.from_user.id)

    text = (
        "📖 Справка по командам\n\n"

        "👤 Пользователь:\n"
        "/business ID - информация о бизнесе/по категории \n"
        "/bizlist - список бизнесов\n"
        "/zbt - список збт\n"
        "/categories - список категорий\n"
        "/support - справка\n"
        "/admin - список администрации\n"
        "/iadmin - профиль админа\n"
        "/rep - проголосовать за админа\n"
        "/topadmin - Топ репутации администрации\n"
        "/bug - отправить предложение по улучшению\n"
        "/profile - посмотреть свой профиль\n"
        "/bs - список активных битв \n"
    )

    if role >= 1:
        text += (
            "\n✏️ Редактор:\n"
            "/vbiz ID Новый владелец - изменение владельца\n"
            "/fbiz ID Фотография - изменение фотографии\n"
            "/cbiz ID Категория - изменение категории\n"
            "/delcbiz ID - удаление категории\n"
            "/dadm ID - изменение должности\n"
            "/addbc - добавить активное битву семей!только для бс!\n"
        )

    if role >= 2:
        text += (
            "\n👑 Создатель:\n"
            "/nbiz ID - Новое название\n"
            "/repadm - изменить репутацию\n"
            "/lbiz ID - Новый адрес\n"
            "/logs - логи\n"
            "/addadm ID - Добавить админа в список\n"
            "/delbiz ID - удалить бизнес\n"
            "/userrole ID - статус роли\n"
            "/stats - cписок пользавателей \n"
            "/addbiz ID | Автоцентр Премиум | Иван Петров | Москва | Автосервис - создание бизнеса\n"
        )

    await message.answer(text)

@dp.message(Command("role"))
async def role(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    role = get_role(message.from_user.id)

    roles = {
        0: "Пользователь",
        1: "Редактор",
        2: "Создатель"
    }

    await message.answer(
        f"Ваша роль: {roles.get(role, 'Неизвестно')}"
    )

@dp.message(Command("userrole"))
async def userrole(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)
    

    if not is_creator(message.from_user.id):
        await message.answer(
            "Недостаточно прав."
        )
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "Пример:\n/userrole 123456789"
        )
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer(
            "ID должен быть числом."
        )
        return

    role = get_role(user_id)

    roles = {
        0: "Пользователь",
        1: "Редактор",
        2: "Создатель"
    }

    await message.answer(
        f"ID: {user_id}\n"
        f"Роль: {roles.get(role, 'Неизвестно')}"
    )

@dp.message(F.text == "📋 Бизнесы")
async def menu_bizlist(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    rows = execute(
        "SELECT id, name FROM businesses ORDER BY id"
    ).fetchall()

    if not rows:
        await message.answer("Список бизнесов пуст.")
        return

    text = "📋 Список бизнесов\n\n"

    for business_id, name in rows:
        text += f"🆔 {business_id} | {name}\n"

    await message.answer(text)

@dp.message(F.text == "📂 Категории")
async def menu_categories(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)
   

    rows = execute(
        """
        SELECT DISTINCT category
        FROM businesses
        WHERE category IS NOT NULL
        AND category != ''
        ORDER BY category
        """
    ).fetchall()

    if not rows:
        await message.answer(
            "Категории отсутствуют."
        )
        return

    text = "📂 Категории\n\n"

    for (category,) in rows:
        text += f"• {category}\n"

    await message.answer(text)

@dp.message(F.text == "ℹ️ Помощь")
async def menu_help(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    role = get_role(message.from_user.id)

    text = (
        "📖 Справка\n\n"
        "/business ID\n"
        "/business Категория\n"
        "/bizlist\n"
        "/categories\n"
        "/role\n"
        "/support\n"
    )

    if role >= 1:
        text += (
            "\n✏️ Редактор:\n"
            "/vbiz\n"
            "/fbiz\n"
            "/cbiz\n"
            "/delcbiz\n"
        )

    if role >= 2:
        text += (
            "\n👑 Создатель:\n"
            "/nbiz\n"
            "/lbiz\n"
            "/delbiz\n"
            "/userrole\n"
        )

    await message.answer(text)

@dp.callback_query(F.data == "zbt_info")
async def zbt_info(callback: CallbackQuery):

    await callback.answer()

    await callback.message.answer(
        "📥 <b>Скачать ЗБТ</b>\n\n"
        "Чтобы скачать ЗБТ, напишите команду "
        "<code>/zbt</code> в личные сообщения с ботом.",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "admins_info")
async def admins_info(callback: CallbackQuery):

    await callback.answer()

    await callback.message.answer(
        "👮 <b>Администраторы</b>\n\n"
        "Чтобы посмотреть список администраторов, "
        "напишите команду <code>/admins</code> в личные сообщения с ботом.",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "report_info")
async def report_info(callback: CallbackQuery):

    await callback.answer()

    await callback.message.answer(
        "📝 <b>Написать жалобу</b>\n\n"
        "Чтобы написать жалобу, напишите команду "
        "<code>/report</code> в личные сообщения с ботом.",
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "start_info")
async def start_info_callback(callback: CallbackQuery):

    await callback.message.answer(
        "ℹ️ <b>Информация</b>\n\n"
        "Чтобы посмотреть полезную информацию, "
        "напишите команду /info в личные сообщения с ботом.",
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data == "start_bs")
async def start_bs_callback(callback: CallbackQuery):

    await callback.message.answer(
        "⚔️ <b>Битва семей</b>\n\n"
        "Чтобы открыть информацию о битве семей, "
        "напишите команду /bs в личные сообщения с ботом.",
        parse_mode="HTML"
    )

    await callback.answer()

@dp.message(Command("addbiz"))
async def addbiz(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)
  

    if not is_creator(message.from_user.id):
        await message.answer("Недостаточно прав.")
        return

    try:
        data = message.text.replace("/addbiz", "", 1).strip()

        parts = [x.strip() for x in data.split("|")]

        if len(parts) != 5:
            raise ValueError

        business_id = int(parts[0])
        name = parts[1]
        owner = parts[2]
        location = parts[3]
        category = parts[4]

    except:
        await message.answer(
            "Пример:\n"
            "/addbiz 15 | Автоцентр Премиум | Иван Петров | Москва | Автосервис"
        )
        return

    execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    )

    if execute(
       "SELECT id FROM businesses WHERE id=%s",
       (business_id,)
    ).fetchone():
        await message.answer(
            "Бизнес с таким ID уже существует."
        )
        return

    execute(
        """
        INSERT INTO businesses
        (id, name, owner, location, category)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            business_id,
            name,
            owner,
            location,
            category
        )
    )

    

    await message.answer(
        f"✅ Бизнес создан.\n\n"
        f"ID: {business_id}\n"
        f"Название: {name}"
    )

@dp.message(Command("logs"))
async def logs(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    if not is_creator(message.from_user.id):
        await message.answer("Недостаточно прав.")
        return

    rows = execute(
        """
        SELECT user_id, action, created_at
        FROM logs
        ORDER BY id DESC
        LIMIT 20
        """
    ).fetchall()

    if not rows:
        await message.answer("Логи пусты.")
        return

    text = "📜 Последние действия\n\n"

    for user_id, action, created_at in rows:
        text += (
            f"👤 {user_id}\n"
            f"📝 {action}\n"
            f"🕒 {created_at}\n\n"
        )

    await message.answer(text)

@dp.message(Command("checkrole"))
async def checkrole(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    
    rows = execute(
        "SELECT * FROM roles"
    ).fetchall()

    await message.answer(str(rows))
    
@dp.callback_query(F.data == "biz")
async def biz(callback: CallbackQuery):

    if not await check_sub(bot, CHANNEL_ID, callback.message):
        await require_sub(callback.message)
        return

    await register_user(bot, OWNER_ID, callback.message)

    await callback.answer()

    await bizlist(callback.message)

@dp.callback_query(F.data == "categories")
async def categories_btn(callback: CallbackQuery):

    if not await check_sub(bot, CHANNEL_ID, callback.message):
        await require_sub(callback.message)
        return

    await register_user(bot, OWNER_ID, callback.message)

    await callback.answer()

    await categories(callback.message)

@dp.callback_query(F.data == "help")
async def help_btn(callback: CallbackQuery):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    await callback.answer()

    await support(callback.message)

async def set_commands(bot):
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="business", description="Поиск бизнеса"),
        BotCommand(command="bizlist", description="Список бизнесов"),
        BotCommand(command="categories", description="Список категорий"),
        BotCommand(command="support", description="Помощь"),
        BotCommand(command="profile", description="Профиль пользователя"),
        BotCommand(command="vbiz", description="Изменение владельца"),
        BotCommand(command="fbiz", description="Изменение фотографии"),
        BotCommand(command="admins", description="Список администрации"),
        BotCommand(command="iadmin", description="Информация о админе"),
        BotCommand(command="deladm", description="Удалить админа из списка"),
        BotCommand(command="dadm", description="Изменить должность"),
        BotCommand(command="rep", description="Проголосвать за репутацию"),
        BotCommand(command="topadmin", description="топ репутации администрации"),
        BotCommand(command="bug", description="Отправить предложение по улучшению"),
        BotCommand(command="bs", description="Посмотреть активные битвы семей"),
        BotCommand(command="profile", description="Посмотреть профиль"),
        BotCommand(command="zbt", description="Открыть список збт"),
        BotCommand(command="addzbt", description="Добавить пост о збт"),
        BotCommand(command="del", description="Удалить пост о збт"),
        BotCommand(command="repadm", description="Изменить репутацию "),
        BotCommand(command="casino", description="Информация о казино"),
        BotCommand(command="carlist", description="Айди автомобилей "),
        BotCommand(command="info", description="Информация для новичков ")
    ]

    await bot.set_my_commands(commands)

@dp.message(Command("clear"))
async def clear_chat(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)
  

    if get_role(message.from_user.id) < 2:
        await message.answer("❌ Команда доступна только создателю.")
        return

    args = message.text.split()

    if len(args) != 2 or not args[1].isdigit():
        await message.answer(
            "Использование:\n/clear 100"
        )
        return

    count = int(args[1])

    for msg_id in range(
        message.message_id - count,
        message.message_id + 1
    ):
        try:
            await bot.delete_message(
                chat_id=message.chat.id,
                message_id=msg_id
            )
        except:
            pass

@dp.message(Command("addadm"))
async def addadm(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    if get_role(message.from_user.id) < 2:
        await message.answer("Недостаточно прав.")
        return

    text = message.text.replace("/addadm", "", 1).strip()

    parts = [x.strip() for x in text.split("|")]

    if len(parts) != 5:
        await message.answer(
            "Пример:\n"
            "/addadm 1 | Willy | https://vk.com/willy | Главный администратор | Руководители"
        )
        return

    try:
        admin_id = int(parts[0])
    except ValueError:
        await message.answer("ID должен быть числом.")
        return

    nickname = parts[1]
    vk = parts[2]
    position = parts[3]
    department = parts[4]

    if execute(
        "SELECT id FROM admins WHERE id=%s",
        (admin_id,)
    ).fetchone():
        await message.answer(
            "Администратор с таким ID уже существует."
        )
        return

    execute(
        """
        INSERT INTO admins
        (id, nickname, vk, position, department, reputation)
        VALUES (%s, %s, %s, %s, %s, 0)
        """,
        (
            admin_id,
            nickname,
            vk,
            position,
            department
        )
    )

    

    add_log(
        message.from_user.id,
        f"Добавил администратора {nickname}"
    )

    await message.answer("✅ Администратор добавлен.")

@dp.message(Command("admins"))
async def admins(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    departments = [
        ("🔴", "Руководители"),
        ("🟣", "Кураторы"),
        ("⚫️", "Технический отдел"),
        ("🟠", "Старшие Администраторы"),
        ("🔵", "Администраторы"),
        ("🟡", "Старший модераторы"),
        ("⚪️", "Модераторы"),
        ("🟢", "Младший модераторы")

    ]

    text = "👮 Администрация Брянска\n"

    for emoji, department in departments:

        rows = execute(
            """
            SELECT id, nickname, position
            FROM admins
            WHERE department=%s
            ORDER BY id
            """,
            (department,)
        ).fetchall()

        if not rows:
            continue

        text += f"\n{emoji} {department}\n\n"

        for admin_id, nickname, position in rows:
            text += f"{admin_id} - {nickname} - {position}\n"

    await message.answer(text)

@dp.message(Command("iadmin"))
async def iadmin(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        await message.answer(
            "Пример:\n/iadmin 1\n/iadmin Nickname"
        )
        return

    search = args[1]


    if search.isdigit():

        admin = execute("""
            SELECT id, nickname, vk, position, reputation, department
            FROM admins
            WHERE id=%s
        """, (int(search),)).fetchone()

    else:

        admin = execute("""
            SELECT id, nickname, vk, position, reputation, department
            FROM admins
            WHERE nickname ILIKE %s
        """, (search,)).fetchone()


    if not admin:
        await message.answer(
            "Администратор не найден."
        )
        return


    admin_id, nickname, vk, position, reputation, department = admin


    rating = execute("""
        SELECT id
        FROM admins
        ORDER BY reputation DESC, nickname
    """).fetchall()


    place = None

    for i, (aid,) in enumerate(rating, start=1):
        if aid == admin_id:
            place = i
            break


    if place == 1:
        medal = "🥇"
    elif place == 2:
        medal = "🥈"
    elif place == 3:
        medal = "🥉"
    else:
        medal = f"#{place}"


    text = (
        "👤 Информация об администраторе\n\n"
        f"🆔 ID: {admin_id}\n"
        f"👤 Ник: {nickname}\n"
        f"🏢 Отдел: {department or 'Не указан'}\n"
        f"💼 Должность: {position}\n\n"
        f"⭐ Репутация: {reputation}\n"
        f"🏆 Место в рейтинге: {medal}\n\n"
        f"🔗 ВКонтакте:\n{vk or 'Не указан'}"
    )


    await message.answer(text)

@dp.message(Command("deladm"))
async def deladm(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    if get_role(message.from_user.id) < 2:
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "Пример:\n/deladm 1"
        )
        return

    try:
        admin_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом.")
        return

    admin = execute(
        "SELECT nickname FROM admins WHERE id=%s",
        (admin_id,)
    ).fetchone()

    if not admin:
        await message.answer("Администратор не найден.")
        return

    nickname = admin[0]

    execute(
        "DELETE FROM admins WHERE id=%s",
        (admin_id,)
    )

    

    add_log(
        message.from_user.id,
        f"Удалил администратора {nickname}"
    )

    await message.answer(
        f"✅ Администратор {nickname} удалён."
    )

@dp.message(Command("dadm"))
async def dadm(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    if get_role(message.from_user.id) < 1:
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split(maxsplit=2)

    if len(args) != 3:
        await message.answer(
            "Пример:\n/dadm 1 Главный администратор"
        )
        return

    try:
        admin_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом.")
        return

    new_position = args[2]

    admin = execute(
        "SELECT nickname FROM admins WHERE id=%s",
        (admin_id,)
    ).fetchone()

    if not admin:
        await message.answer("Администратор не найден.")
        return

    nickname = admin[0]

    execute(
        """
        UPDATE admins
        SET position=%s
        WHERE id=%s
        """,
        (
            new_position,
            admin_id
        )
    )

    

    add_log(
        message.from_user.id,
        f"Изменил должность {nickname} -> {new_position}"
    )

    await message.answer(
        "✅ Должность изменена."
    )

@dp.message(Command("repadm"))
async def repadm(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    if get_role(message.from_user.id) < 1:
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split()

    if len(args) != 3:
        await message.answer(
            "Пример:\n/repadm 1 15"
        )
        return

    try:
        admin_id = int(args[1])
        reputation = int(args[2])
    except ValueError:
        await message.answer(
            "ID и репутация должны быть числами."
        )
        return

    admin = execute(
        "SELECT nickname FROM admins WHERE id=%s",
        (admin_id,)
    ).fetchone()

    if not admin:
        await message.answer("Администратор не найден.")
        return

    nickname = admin[0]

    execute(
        """
        UPDATE admins
        SET reputation=%s
        WHERE id=%s
        """,
        (
            reputation,
            admin_id
        )
    )

    

    add_log(
        message.from_user.id,
        f"Изменил репутацию {nickname} -> {reputation}"
    )

    await message.answer(
        f"✅ Репутация администратора {nickname} изменена на {reputation}."
    )
    
@dp.message(Command("rep"))
async def rep(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    args = message.text.split()

    if len(args) != 3:
        await message.answer(
            "Пример:\n"
            "/rep 1 +\n"
            "/rep 1 -"
        )
        return

    try:
        admin_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом.")
        return

    if args[2] == "+":
        vote = 1
    elif args[2] == "-":
        vote = -1
    else:
        await message.answer("Используйте только + или -")
        return

    admin = execute(
        "SELECT nickname FROM admins WHERE id=%s",
        (admin_id,)
    ).fetchone()

    if not admin:
        await message.answer("Администратор не найден.")
        return

    if execute(
        """
        SELECT vote
        FROM admin_votes
        WHERE user_id=%s AND admin_id=%s
        """,
        (
            message.from_user.id,
            admin_id
        )
    ).fetchone():
        await message.answer(
            "Вы уже оценивали этого администратора."
        )
        return

    execute(
        """
        INSERT INTO admin_votes
        (user_id, admin_id, vote)
        VALUES (%s, %s, %s)
        """,
        (
            message.from_user.id,
            admin_id,
            vote
        )
    )

    execute(
        """
        UPDATE admins
        SET reputation = reputation + %s
        WHERE id=%s
        """,
        (
            vote,
            admin_id
        )
    )

    

    await message.answer(
        "Спасибо за вашу оценку!"
    )

@dp.message(Command("topadmin"))
async def topadmin(message: Message):

    if get_role(message.from_user.id) < 1:
        return

    best = execute("""
        SELECT nickname, position, reputation
        FROM admins
        ORDER BY reputation DESC
        LIMIT 3
    """).fetchall()

    worst = execute("""
        SELECT nickname, position, reputation
        FROM admins
        ORDER BY reputation ASC
        LIMIT 3
    """).fetchall()

    text = "🏆 Топ администраторов\n\n"

    text += "📈 Топ лучших:\n"

    medals = ["🥇", "🥈", "🥉"]

    if best:
        for i, (nick, pos, rep) in enumerate(best):
            text += (
                f"{medals[i]} {nick}\n"
                f"💼 {pos}\n"
                f"⭐ {rep}\n\n"
            )
    else:
        text += "Нет данных.\n\n"

    text += "📉 Топ худших:\n"

    if worst:
        for i, (nick, pos, rep) in enumerate(worst):
            text += (
                f"{medals[i]} {nick}\n"
                f"💼 {pos}\n"
                f"⭐ {rep}\n\n"
            )
    else:
        text += "Нет данных."

    await message.answer(text)

@dp.message(Command("bug"))
async def bug(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        await message.answer(
            "Пример:\n"
            "/bug Добавить поиск по владельцу"
        )
        return

    text = args[1]

    await bot.send_message(
        OWNER_ID,
        (
            "🐞 Новое предложение\n\n"
            f"👤 Пользователь: {message.from_user.full_name}\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"📎 Username: @{message.from_user.username if message.from_user.username else 'отсутствует'}\n\n"
            f"💬 Сообщение:\n{text}"
        )
    )

    await message.answer(
        "✅ Ваше предложение успешно отправлено разработчику."
    )

@dp.message(Command("broadcast"))
async def broadcast(message: Message):

    if not is_creator(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        await message.answer(
            "Пример:\n"
            "/broadcast Текст сообщения"
        )
        return

    text = args[1]

    users_sent = 0
    chats_sent = 0

    for (user_id,) in execute("SELECT user_id FROM users").fetchall():
        try:
            await bot.send_message(user_id, text)
            users_sent += 1
        except:
            pass

    execute("SELECT chat_id FROM chats")

    for (chat_id,) in execute("SELECT chat_id FROM chats").fetchall():
        try:
            await bot.send_message(chat_id, text)
            chats_sent += 1
        except:
            pass

    await message.answer(
        f"✅ Рассылка завершена.\n\n"
        f"👤 Пользователям: {users_sent}\n"
        f"👥 Группам: {chats_sent}"
    )

@dp.message(Command("stats"))
async def stats(message: Message):

    if not is_creator(message.from_user.id):
        return

    users = execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    chats = execute(
        "SELECT COUNT(*) FROM chats"
    ).fetchone()[0]

    businesses = execute(
        "SELECT COUNT(*) FROM businesses"
    ).fetchone()[0]

    admins = execute(
        "SELECT COUNT(*) FROM admins"
    ).fetchone()[0]

    await message.answer(
        f"📊 Статистика бота\n\n"
        f"👤 Пользователей: {users}\n"
        f"👥 Групп: {chats}\n"
        f"🏢 Бизнесов: {businesses}\n"
        f"🛡 Администраторов: {admins}"
    )

@dp.message(Command("addbs"))
async def addbs(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    if get_role(message.from_user.id) < 1:
        return

    args = message.text.split()

    if len(args) != 3:
        await message.answer(
            "Пример:\n"
            "/addbs 17:00 1-5"
        )
        return

    end = args[1].replace(";", ":").replace(".", ":")
    location = args[2]

    try:
        datetime.strptime(end, "%H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат времени.\nПример: 17:00")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    end_time = f"{today} {end}:00"

    execute("DELETE FROM family_battle")

    execute(
        """
        INSERT INTO family_battle(location, end_time)
        VALUES(%s, %s)
        """,
        (location, end_time)
    )

    row = execute(
        "SELECT location, end_time FROM family_battle LIMIT 1"
    ).fetchone()

    await message.answer(f"DEBUG: {row}")

    await message.answer("✅ Активная БС добавлена.")

@dp.message(Command("bs"))
async def bs(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    row = execute(
        """
        SELECT location, end_time
        FROM family_battle
        LIMIT 1
        """
    ).fetchone()

    if not row:
        await message.answer("Активных битв семей нет.")
        return

    location, end_time = row

    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)

    if datetime.now() >= end_time:
        execute("DELETE FROM family_battle")
        await message.answer("Активных битв семей нет.")
        return

    await message.answer(
        f"⚔ <b>Активная битва семей</b>\n\n"
        f"📍 Местоположение: <code>/gps {location}</code>\n"
        f"🕒 Время битвы: <b>{end_time.strftime('%H:%M')}</b>",
        parse_mode="HTML"
    )

@dp.message(Command("delbs"))
async def delbs(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    if get_role(message.from_user.id) < 1:
        await message.answer("Недостаточно прав.")
        return

    execute("DELETE FROM family_battle")


    await message.answer("✅ Активная битва семей удалена.")

@dp.message(Command("profile"))
async def profile(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)


    args = message.text.split()

    target_id = message.from_user.id

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id

    elif len(args) == 2:
        if args[1].isdigit():
            target_id = int(args[1])
        else:
            await message.answer("Укажите корректный ID.")
            return

    user = execute(
        """
        SELECT first_name, username, reg_date
        FROM users
        WHERE user_id=%s
        """,
        (target_id,)
    ).fetchone()

    if not user:
        await message.answer("Пользователь не найден.")
        return

    first_name, username, reg_date = user

    role = "Пользователь"

    if target_id in ADMINS:
        role = "Редактор"

    if is_creator(target_id):
        role = "Создатель"

    await message.answer(
        f"""
👤 <b>Профиль пользователя</b>

🆔 ID: <code>{target_id}</code>

👤 Ник:
{first_name}

🔗 Username:
@{username if username else 'нет'}

⭐ Роль:
{role}

📅 Регистрация:
{reg_date}

""",
        parse_mode="HTML"
    )

@dp.message(Command("zbt"))
async def zbt(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)
    
    posts = execute("""
        SELECT chat_id, message_id
        FROM zbt_posts
        ORDER BY id
    """).fetchall()

    if not posts:
        await message.answer("Постов пока нет.")
        return

    for chat_id, message_id in posts:

        await bot.copy_message(
            chat_id=message.from_user.id,
            from_chat_id=chat_id,
            message_id=message_id
        )

@dp.message(Command("delzbt"))
async def delzbt(message: Message):

    if not is_creator(message.from_user.id):
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer("Пример:\n/delzbt 1")
        return

    execute(
        "DELETE FROM zbt_posts WHERE id=%s",
        (args[1],)
    )

    

    await message.answer("✅ Пост удалён.")

@dp.message(Command("addzbt"))
async def addzbt(message: Message):

    if not is_creator(message.from_user.id):
        return

    waiting_zbt.add(message.from_user.id)

    await message.answer(
        "📨 Отправьте готовый пост (текст, фото, документ, видео и т.д.)"
    )

@dp.message(Command("unbani"))
async def unbani(message: Message):

    if not is_creator(message.from_user.id):
        return

    if message.chat.type == "private":
        await message.answer("Команда работает только в группах.")
        return

    if not message.reply_to_message:
        await message.answer("Ответьте на сообщение пользователя.")
        return

    user = message.reply_to_message.from_user

    try:
        await bot.unban_chat_member(
            chat_id=message.chat.id,
            user_id=user.id,
            only_if_banned=True
        )

        await message.answer(
            f"✅ {user.full_name} был разбанен."
        )

    except Exception as e:
        await message.answer(f"Ошибка:\n{e}")

@dp.message(Command("bani"))
async def bani(message: Message):

    print("BANI COMMAND")

    if not is_creator(message.from_user.id):
        return

    if message.chat.type == "private":
        await message.answer("Команда работает только в группах.")
        return

    if not message.reply_to_message:
        await message.answer("Ответьте на сообщение пользователя.")
        return

    user = message.reply_to_message.from_user

    try:
        await bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=user.id
        )

        await message.answer(
            f"✅ {user.full_name} был заблокирован."
        )

    except Exception as e:
        await message.answer(f"Ошибка:\n{e}")

@dp.message(Command("addo"))
async def addo(message: Message):

    if not await check_sub(bot, CHANNEL_ID, message):
        await require_sub(message)
        return

    await register_user(bot, OWNER_ID, message)

    if get_role(message.from_user.id) < 1:
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "Пример:\n"
            "/addo 1 Руководители"
        )
        return

    try:
        admin_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом.")
        return

    department = " ".join(args[2].split())

    if not execute(
        "SELECT id FROM admins WHERE id=%s",
        (admin_id,)
    ).fetchone():
        await message.answer(
            "Администратор не найден."
        )
        return

    execute(
        """
        UPDATE admins
        SET department=%s
        WHERE id=%s
        """,
        (
            department,
            admin_id
        )
    )

    add_log(
        message.from_user.id,
        f"Изменил отдел администратора {admin_id} на '{department}'"
    )

    await message.answer(
        f"✅ Администратору {admin_id} установлен отдел «{department}»."
    )

@dp.message(Command("addkaz"))
async def addkaz(message: Message):

    if get_role(message.from_user.id) < 1:
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split(maxsplit=2)

    if len(args) != 3:
        await message.answer(
            "Пример:\n"
            "/addkaz Willy 25.07.2026"
        )
        return

    owner = args[1]
    catch_date = args[2]

    take_date = datetime.now().strftime("%d.%m.%Y %H:%M")

    execute("DELETE FROM casino")

    execute(
        """
        INSERT INTO casino
        (id, last_owner, last_take_date, catch_date)
        VALUES (1, %s, %s, %s)
        """,
        (
            owner,
            take_date,
            catch_date
        )
    )

    add_log(
        message.from_user.id,
        f"Добавил казино ({owner})"
    )

    await message.answer("✅ Информация о казино обновлена.")

@dp.message(Command("casino"))
async def casino(message: Message):

    row = execute(
        """
        SELECT
            last_owner,
            last_take_date,
            catch_date
        FROM casino
        LIMIT 1
        """
    ).fetchone()

    if not row:
        await message.answer("❌ Информация о казино отсутствует.")
        return

    owner, take_date, catch_date = row

    text = (
        "🎰 Информация о казино\n\n"
        f"👤 Последний владелец:\n{owner}\n\n"
        f"🎯 Дата ловли:\n{catch_date}"
    )
    await message.answer(text)

@dp.message(Command("delkaz"))
async def delkaz(message: Message):

    if get_role(message.from_user.id) < 1:
        await message.answer("Недостаточно прав.")
        return

    execute("DELETE FROM casino")

    add_log(
        message.from_user.id,
        "Удалил информацию о казино"
    )

    await message.answer(
        "✅ Информация о казино удалена."
    )

@dp.message(Command("upload"))
async def upload(message: Message):
    waiting_upload[message.from_user.id] = datetime.now()

    await message.answer(
        "📤 Отправьте фото или видео в течение 5 минут.\n"
        "После этого я загружу файл и пришлю ссылку."
    )

@dp.message(F.photo | F.video)
async def upload_file(message: Message):

    start_time = waiting_upload.get(message.from_user.id)

    if not start_time:
        return

    if datetime.now() - start_time > timedelta(minutes=5):
        waiting_upload.pop(message.from_user.id, None)
        await message.answer("⌛ Время ожидания истекло. Напишите /upload ещё раз.")
        return

    waiting_upload.pop(message.from_user.id, None)

    if message.from_user.id not in UPLOAD_WAIT:
        return

    if message.photo:
        file_id = message.photo[-1].file_id
        filename = f"{message.from_user.id}.jpg"
        resource = "image"

    else:
        file_id = message.video.file_id
        filename = f"{message.from_user.id}.mp4"
        resource = "video"

    file = await bot.get_file(file_id)

    await bot.download_file(file.file_path, filename)

    result = cloudinary.uploader.upload(
        filename,
        resource_type=resource
    )

    os.remove(filename)

    UPLOAD_WAIT.remove(message.from_user.id)

    await message.answer(
        f"✅ Ссылка:\n{result['secure_url']}"
    )

@dp.message(Command("report"))
async def report(message: Message):

    # Только личные сообщения
    if message.chat.type != "private":
        await message.answer(
            "❌ Команда доступна только в личных сообщениях с ботом."
        )
        return

    # Сначала проверяем, есть ли свободный старый номер
    free_id = execute(
        """
        SELECT id
        FROM free_report_ids
        ORDER BY id
        LIMIT 1
        """
    ).fetchone()

    if free_id:
        report_id = free_id[0]

        # Убираем номер из списка свободных
        execute(
            """
            DELETE FROM free_report_ids
            WHERE id=%s
            """,
            (report_id,)
        )

        # Создаём репорт с этим номером
        execute(
            """
            INSERT INTO reports
            (id, user_id, username)
            VALUES(%s, %s, %s)
            """,
            (
                report_id,
                message.from_user.id,
                message.from_user.username
            )
        )

    else:
        # Если свободных старых номеров нет —
        # PostgreSQL сам выдаёт следующий SERIAL ID
        report_id = execute(
            """
            INSERT INTO reports
            (user_id, username)
            VALUES(%s, %s)
            RETURNING id
            """,
            (
                message.from_user.id,
                message.from_user.username
            )
        ).fetchone()[0]

    active_reports[message.from_user.id] = report_id

    await message.answer(
        f"📝 Обращение #{report_id} создано.\n\n"
        "Теперь отправляйте текст, фото, видео или документы.\n\n"
        "Когда закончите — используйте /endreport"
    )

@dp.message(Command("endreport"))
async def end_report(message: Message):

    if message.from_user.id not in active_reports:
        await message.answer("У вас нет активного обращения.")
        return

    report_id = active_reports.pop(message.from_user.id)

    await message.answer(
        f"✅ Обращение #{report_id} отправлено редакторам."
    )

@dp.message(Command("reports"))
async def reports(message: Message):

    if message.from_user.id not in ADMINS and not is_creator(message.from_user.id):
        return

    args = message.text.split()

    if len(args) > 2:
        await message.answer(
            "Использование:\n"
            "/reports\n"
            "/reports 2"
        )
        return

    try:
        page = int(args[1]) if len(args) == 2 else 1
    except ValueError:
        await message.answer(
            "❌ Номер страницы должен быть числом."
        )
        return

    if page < 1:
        await message.answer(
            "❌ Номер страницы должен быть больше 0."
        )
        return

    limit = 20
    offset = (page - 1) * limit

    # Количество ВСЕХ обращений
    total = execute(
        """
        SELECT COUNT(*)
        FROM reports
        """
    ).fetchone()[0]

    if total == 0:
        await message.answer(
            "📭 Обращений нет."
        )
        return

    total_pages = (total + limit - 1) // limit

    if page > total_pages:
        await message.answer(
            f"❌ Такой страницы нет.\n"
            f"Всего страниц: {total_pages}"
        )
        return

    rows = execute(
        """
        SELECT id, user_id, username, created_at, status, verdict
        FROM reports
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """,
        (
            limit,
            offset
        )
    ).fetchall()

    text = (
        f"📋 <b>Обращения</b>\n"
        f"Страница {page}/{total_pages}\n\n"
    )

    for rep_id, user_id, username, created_at, status, verdict in rows:

        username = f"@{username}" if username else "нет"

        if status == "closed":
            verdict_text = verdict if verdict else "не указан"

            text += (
                f"#{rep_id} / {verdict_text}\n"
                f"👤 {username}\n"
                f"🆔 <code>{user_id}</code>\n"
                f"📅 {created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"🔒 Закрыто\n\n"
            )

        else:
            text += (
                f"#{rep_id}\n"
                f"👤 {username}\n"
                f"🆔 <code>{user_id}</code>\n"
                f"📅 {created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"🟢 Открыто\n\n"
            )

    text += "────────────\n"

    if page < total_pages:
        text += f"➡️ Следующая страница: /reports {page + 1}"

    await message.answer(
        text,
        parse_mode="HTML"
    )

@dp.message(Command("reportinfo"))
async def reportinfo(message: Message):

    if message.from_user.id not in ADMINS and not is_creator(message.from_user.id):
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "Использование:\n/reportinfo ID"
        )
        return

    try:
        report_id = int(args[1])
    except ValueError:
        await message.answer("ID обращения должен быть числом.")
        return

    report = execute(
        """
        SELECT user_id, username, created_at
        FROM reports
        WHERE id=%s
        """,
        (report_id,)
    ).fetchone()

    if not report:
        await message.answer("Обращение не найдено.")
        return

    user_id, username, created = report

    rows = execute(
        """
        SELECT sender, text, file_id, file_type
        FROM report_messages
        WHERE report_id=%s
        ORDER BY id
        """,
        (report_id,)
    ).fetchall()

    history = ""

    for sender, text, file_id, file_type in rows:

        prefix = (
            "👤 Пользователь"
            if sender == "user"
            else "👮 Редактор"
        )

        # Текст
        if text:

            # Не показываем команды в истории
            if text.startswith("/"):
                continue

            history += (
                f"{prefix}\n"
                f"{text}\n\n"
            )

        # Файл
        if file_id:

            if file_type == "photo":
                history += (
                    f"{prefix}\n"
                    f"📷 Фото\n\n"
                )

            elif file_type == "video":
                history += (
                    f"{prefix}\n"
                    f"🎥 Видео\n\n"
                )

            elif file_type == "document":
                history += (
                    f"{prefix}\n"
                    f"📄 Документ\n\n"
                )

    await message.answer(
        f"""
📋 <b>Обращение #{report_id}</b>

👤 @{username if username else 'нет'}
🆔 <code>{user_id}</code>
📅 {created.strftime('%d.%m.%Y %H:%M')}

────────────

{history if history else 'Сообщений нет.'}
""",
        parse_mode="HTML"
    )

    # Отправляем файлы отдельно
    for sender, text, file_id, file_type in rows:

        if not file_id:
            continue

        # Если текст был командой — сам файл всё равно показываем
        prefix = (
            "👤 Пользователь"
            if sender == "user"
            else "👮 Редактор"
        )

        if file_type == "photo":

            await message.answer_photo(
                file_id,
                caption=prefix
            )

        elif file_type == "video":

            await message.answer_video(
                file_id,
                caption=prefix
            )

        elif file_type == "document":

            await message.answer_document(
                file_id,
                caption=prefix
            )

@dp.message(Command("repsms"))
async def repsms(message: Message):

    if message.from_user.id not in ADMINS and not is_creator(message.from_user.id):
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "Использование:\n"
            "/repsms ID"
        )
        return

    report_id = int(args[1])

    report = execute(
        """
        SELECT user_id
        FROM reports
        WHERE id=%s AND status='open'
        """,
        (report_id,)
    ).fetchone()

    if not report:
        await message.answer("Обращение не найдено.")
        return

    user_id = report[0]

    waiting_rep_answer[message.from_user.id] = (report_id, user_id)

    await message.answer(
        f"✍ Напишите ответ пользователю по обращению #{report_id}"
    )

@dp.message(Command("closerep"))
async def closerep(message: Message):

    if message.from_user.id not in ADMINS and not is_creator(message.from_user.id):
        return

    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "Использование:\n"
            "/closerep ID Вердикт\n\n"
            "Пример:\n"
            "/closerep 15 Нарушение правил"
        )
        return

    try:
        report_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID обращения должен быть числом.")
        return

    verdict = args[2].strip()

    if not verdict:
        await message.answer("❌ Укажите вердикт.")
        return

    report = execute(
        """
        SELECT user_id
        FROM reports
        WHERE id=%s AND status='open'
        """,
        (report_id,)
    ).fetchone()

    if not report:
        await message.answer(
            "❌ Обращение не найдено или уже закрыто."
        )
        return

    user_id = report[0]

    execute(
        """
        UPDATE reports
        SET status='closed',
            verdict=%s,
            closed_at=NOW()
        WHERE id=%s
        """,
        (
            verdict,
            report_id
        )
    )

    await bot.send_message(
        user_id,
        f"✅ Ваше обращение #{report_id} было закрыто редактором.\n\n"
        f"📋 Вердикт: {verdict}"
    )

    await message.answer(
        f"✅ Обращение #{report_id} закрыто.\n"
        f"📋 Вердикт: {verdict}"
    )

@dp.message(Command("delrep"))
async def delrep(message: Message):

    if message.from_user.id not in ADMINS and not is_creator(message.from_user.id):
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "Использование:\n"
            "/delrep ID"
        )
        return

    try:
        report_id = int(args[1])
    except ValueError:
        await message.answer(
            "❌ ID обращения должен быть числом."
        )
        return

    report = execute(
        """
        SELECT id
        FROM reports
        WHERE id=%s
        """,
        (report_id,)
    ).fetchone()

    if not report:
        await message.answer(
            "❌ Обращение не найдено."
        )
        return

    # Удаляем сообщения этого обращения
    execute(
        """
        DELETE FROM report_messages
        WHERE report_id=%s
        """,
        (report_id,)
    )

    # Удаляем само обращение
    execute(
        """
        DELETE FROM reports
        WHERE id=%s
        """,
        (report_id,)
    )

    # Добавляем номер в список свободных
    execute(
        """
        INSERT INTO free_report_ids(id)
        VALUES(%s)
        ON CONFLICT (id) DO NOTHING
        """,
        (report_id,)
    )

    # Если удалённый репорт был активным у пользователя —
    # убираем его из active_reports
    for user_id, active_report_id in list(active_reports.items()):
        if active_report_id == report_id:
            del active_reports[user_id]

    await message.answer(
        f"🗑 Обращение #{report_id} удалено.\n"
        f"♻ Номер #{report_id} снова доступен для нового обращения."
    )

@dp.message(F.text | F.photo | F.video | F.document)
async def report_messages(message: Message):

    user_id = message.from_user.id

    # ==========================================
    # 1. РЕДАКТОР ОТВЕЧАЕТ ЧЕРЕЗ /repsms
    # ==========================================

    if user_id in waiting_rep_answer:

        # Команды не считаем ответом
        if message.text and message.text.startswith("/"):
            await message.answer(
                "❌ Сейчас ожидается текст ответа пользователю."
            )
            return

        report_id, target_user_id = waiting_rep_answer.pop(user_id)

        text = message.text if message.text else None

        # Ответ редактора сохраняем в историю
        execute(
            """
            INSERT INTO report_messages
            (report_id, sender, text, file_id, file_type)
            VALUES(%s,%s,%s,%s,%s)
            """,
            (
                report_id,
                "editor",
                text,
                None,
                None
            )
        )

        await bot.send_message(
            target_user_id,
            f"📨 Ответ редактора\n\n{text}"
        )

        await message.answer(
            f"✅ Ответ по обращению #{report_id} отправлен."
        )

        return


    # ==========================================
    # 2. ПОЛЬЗОВАТЕЛЬ ПИШЕТ В /report
    # ==========================================

    if user_id in active_reports:

        # Команды не записываем в историю
        if message.text and message.text.startswith("/"):

            await message.answer(
                "❌ Вы находитесь в активном обращении.\n\n"
                "Чтобы закончить его, используйте /endreport"
            )
            return

        report_id = active_reports[user_id]

        text = message.text if message.text else None

        file_id = None
        file_type = None

        if message.photo:
            file_id = message.photo[-1].file_id
            file_type = "photo"

        elif message.video:
            file_id = message.video.file_id
            file_type = "video"

        elif message.document:
            file_id = message.document.file_id
            file_type = "document"

        execute(
            """
            INSERT INTO report_messages
            (report_id, sender, text, file_id, file_type)
            VALUES(%s,%s,%s,%s,%s)
            """,
            (
                report_id,
                "user",
                text,
                file_id,
                file_type
            )
        )

        return

@dp.message()
async def save_zbt(message: Message):

    if message.from_user.id not in waiting_zbt:
        return

    waiting_zbt.remove(message.from_user.id)

    execute(
        """
        INSERT INTO zbt_posts(chat_id, message_id)
        VALUES(%s, %s)
        """,
        (
            message.chat.id,
            message.message_id
        )
    )



    await message.answer("✅ Пост успешно сохранён.")

@dp.message()
async def save_chat(message: Message):

    if message.chat.type in ["group", "supergroup"]:

        execute(
            "INSERT OR IGNORE INTO chats(chat_id) VALUES(%s)",
            (message.chat.id,)
        )

        

async def main():
    print("BOT STARTED")
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
