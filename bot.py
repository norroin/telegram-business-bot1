
import os
import asyncio
import init_db

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


TOKEN = os.getenv("TOKEN")
ADMINS = [5639087435]

bot = Bot(TOKEN)
dp = Dispatcher()

waiting_zbt = set()

CHANNEL_ID = -1002484763518
OWNER_ID = 5639087435

async def check_sub(message: Message):
    try:
        member = await bot.get_chat_member(
            CHANNEL_ID,
            message.from_user.id
        )

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]
    except:
        return False


from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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


async def register_user(message: Message):
    execute(
        "SELECT user_id FROM users WHERE user_id=%s",
        (message.from_user.id,)
    )

    user = cur.fetchone()

    if not user:
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
        db.commit()

        await bot.send_message(
            OWNER_ID,
            f"""🆕 Новый пользователь

👤 {message.from_user.full_name}
🆔 {message.from_user.id}
🔗 @{message.from_user.username if message.from_user.username else 'нет'}
"""
        )


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
        db.commit()

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

    if not await check_sub(message):
        await require_sub(message)
        return

    await register_user(message)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏢 Бизнесы", callback_data="biz")],
            [InlineKeyboardButton(text="📂 Категории", callback_data="categories")],
            [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
        ]
    )

    await message.answer(
        "Добро пожаловать!",
        reply_markup=kb
    )

@dp.message(Command("business"))
async def business(message: Message):
    
    if not await check_sub(message):
        await require_sub(message)
        return

    await register_user(message)
    
    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        await message.answer(
            "Пример:\n/business 15\nили\n/business Автосервис"
        )
        return

    search = args[1]

    # Поиск по ID
    if search.isdigit():
        execute(
            """
            SELECT name, owner, location, photo_id, category
            FROM businesses
            WHERE id=%s
            """,
            (search,)
        )

        row = cur.fetchone()

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
        execute(
        """
        SELECT id, name
        FROM businesses
        WHERE name LIKE %s
        ORDER BY name
        """,
        (f"%{search}%",)
    )

    name_rows = cur.fetchall()

    if name_rows:
        text = "🔎 Найдено по названию:\n\n"

        for business_id, name in name_rows:
            text += f"🆔 {business_id} | {name}\n"

        await message.answer(text)
        return

    # Поиск по категории
        execute(
        """
        SELECT id, name
        FROM businesses
        WHERE category=%s
        ORDER BY name
        """,
        (search,)
    )

    rows = cur.fetchall()

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
    
    if not await check_sub(message):
        await require_sub(message)
        return

    await register_user(message)
    
    execute(
        "SELECT id, name FROM businesses ORDER BY id"
    )

    rows = cur.fetchall()

    if not rows:
        
        await message.answer("Список бизнесов пуст.")
        return

    text = "📋 Список бизнесов\n\n"

    for business_id, name in rows:
        text += f"{business_id} - {name}\n"

    await message.answer(text)

@dp.message(Command("admintab"))
async def admintab(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

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

    if not await check_sub(message):
        await require_sub(message)
        return
    
    current = await state.get_state()

    if current:
        await state.clear()
        await message.answer("Текущее действие отменено.")
    else:
        await message.answer("Нет активного действия.")

@dp.message(F.text == "➕ Добавить бизнес")
async def add_start(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return
    
    if message.from_user.id not in ADMINS:
        return

    await state.set_state(AddBusiness.id)
    await message.answer("Введите ID бизнеса")


@dp.message(AddBusiness.name)
async def add_name(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return

    await state.update_data(name=message.text)
    await state.set_state(AddBusiness.owner)
    await message.answer("Введите владельца")

@dp.message(AddBusiness.id)
async def add_id(message: Message, state: FSMContext):

    if not await check_sub(message):
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

        execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    )

    if cur.fetchone():
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

    if not await check_sub(message):
        await require_sub(message)
        return
    
    await state.update_data(owner=message.text)
    await state.set_state(AddBusiness.category)
    await message.answer("Введите категорию")


@dp.message(AddBusiness.category)
async def add_category(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return
    
    await state.update_data(category=message.text)
    await state.set_state(AddBusiness.location)
    await message.answer("Введите адрес")


@dp.message(AddBusiness.location)
async def add_location(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return
    
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

        db.commit()

    await state.clear()
    await message.answer("Бизнес добавлен.")

@dp.message(F.text == "👤 Изменить владельца")
async def owner_start(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return
    
    await state.set_state(ChangeOwner.business_id)
    await message.answer("Введите ID бизнеса")

@dp.message(ChangeOwner.business_id)
async def owner_bid(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return
    
    await state.update_data(id=message.text)
    await state.set_state(ChangeOwner.owner)
    await message.answer("Введите нового владельца")

@dp.message(ChangeOwner.owner)
async def owner_save(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return
    
    data = await state.get_data()

        execute(
        "UPDATE businesses SET owner=%s WHERE id=%s",
        (message.text, data["id"])
    )
        db.commit()

    await state.clear()
    await message.answer("Владелец изменён.")

@dp.message(F.text == "📍 Изменить адрес")
async def location_start(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return
    
    await state.set_state(ChangeLocation.business_id)
    await message.answer("Введите ID бизнеса")

@dp.message(ChangeLocation.business_id)
async def location_bid(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return
    
    await state.update_data(id=message.text)
    await state.set_state(ChangeLocation.location)
    await message.answer("Введите новый адрес")

@dp.message(ChangeLocation.location)
async def location_save(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return
    
    data = await state.get_data()

        execute(
        "UPDATE businesses SET location=%s WHERE id=%s",
        (message.text, data["id"])
    )
        db.commit()

    await state.clear()
    await message.answer("Адрес обновлён.")

@dp.message(F.text == "📷 Добавить фото")
async def photo_start(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return
    
    await state.set_state(UploadPhoto.business_id)
    await message.answer("Введите ID бизнеса")

@dp.message(UploadPhoto.business_id)
async def photo_bid(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return
    
    await state.update_data(id=message.text)
    await state.set_state(UploadPhoto.photo)
    await message.answer("Отправьте фотографию")

@dp.message(UploadPhoto.photo, F.photo)
async def photo_save(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return
    
    data = await state.get_data()

    photo_id = message.photo[-1].file_id

        execute(
        "UPDATE businesses SET photo_id=%s WHERE id=%s",
        (photo_id, data["id"])
    )
        db.commit()

    await state.clear()
    await message.answer("Фото сохранено.")


@dp.message(Command("setrole"))
async def set_role(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

    if message.from_user.id not in ADMINS:
        return

    args = message.text.split()

    if len(args) != 3:
        await message.answer(
            "Пример:\n/setrole 123456789 1"
        )
        return

    user_id = int(args[1])
    role = int(args[2])

    if role not in [0, 1, 2]:
        await message.answer(
            "0 - Пользователь\n"
            "1 - Редактор\n"
            "2 - Создатель"
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

        db.commit()

    await message.answer(
        f"Роль {role} выдана пользователю {user_id}"
    )

@dp.message(Command("cbiz"))
async def cbiz(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return
    
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
        db.commit()

    await message.answer("Категория сохранена.")

@dp.message(Command("delcbiz"))
async def delcbiz(message: Message):
    
    if not await check_sub(message):
        await require_sub(message)
        return
    
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

        db.commit()

    await message.answer(
        "Категория удалена."
    )

@dp.message(Command("nbiz"))
async def nbiz(message: Message):
    
    if not await check_sub(message):
        await require_sub(message)
        return
    
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

        execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    )

    if not cur.fetchone():
        await message.answer("Бизнес не найден.")
        return

        execute(
        "UPDATE businesses SET name=%s WHERE id=%s",
        (new_name, business_id)
    )

        db.commit()

    await message.answer(
        "Название бизнеса изменено."
    )

@dp.message(Command("lbiz"))
async def lbiz(message: Message):
    
    if not await check_sub(message):
        await require_sub(message)
        return
    
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

        execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    )

    if not cur.fetchone():
        await message.answer("Бизнес не найден.")
        return

        execute(
        "UPDATE businesses SET location=%s WHERE id=%s",
        (new_location, business_id)
    )

        db.commit()

    await message.answer(
        "Адрес бизнеса изменён."
    )

@dp.message(Command("delbiz"))
async def delbiz(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

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

        execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    )

    if not cur.fetchone():
        await message.answer("Бизнес не найден.")
        return

        execute(
        "DELETE FROM businesses WHERE id=%s",
        (business_id,)
    )

        db.commit()

    add_log(
        message.from_user.id,
        f"Удалил бизнес {business_id}"
    )

    await message.answer(
        "Бизнес удалён."
    )
    
@dp.message(Command("vbiz"))
async def vbiz(message: Message):
    
    if not await check_sub(message):
        await require_sub(message)
        return
    
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

        execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    )

    if not cur.fetchone():
        await message.answer("Бизнес не найден.")
        return

        execute(
        "UPDATE businesses SET owner=%s WHERE id=%s",
        (new_owner, business_id)
    )

        db.commit()

    add_log(
    message.from_user.id,
    f"Изменил владельца бизнеса {business_id}"
    )

    await message.answer(
        "Владелец бизнеса изменён."
    )

@dp.message(Command("fbiz"))
async def fbiz(message: Message, state: FSMContext):

    if not await check_sub(message):
        await require_sub(message)
        return

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

        execute(
        "SELECT id FROM businesses WHERE id=%s",
        (business_id,)
    )

    if not cur.fetchone():
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

    if not await check_sub(message):
        await require_sub(message)
        return
    
    data = await state.get_data()

    photo_id = message.photo[-1].file_id

        execute(
        "UPDATE businesses SET photo_id=%s WHERE id=%s",
        (photo_id, data["id"])
    )

        db.commit()

    await state.clear()

    await message.answer(
        "Фотография бизнеса обновлена."
    )

@dp.message(Command("categories"))
async def categories(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

    await register_user(message)
    
        execute(
        """
        SELECT DISTINCT category
        FROM businesses
        WHERE category IS NOT NULL
        AND category != ''
        ORDER BY category
        """
    )

    rows = cur.fetchall()

    if not rows:
        await message.answer("Категории отсутствуют.")
        return

    text = "📂 Категории\n\n"

    for (category,) in rows:
        text += f"• {category}\n"

    await message.answer(text)

@dp.message(Command("support"))
async def support(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

    await register_user(message)

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
        "/iadmin - профиль админи\n"
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
            "/addadm ID - Добавить админа в список\n"
            "/delbiz ID - удалить бизнес\n"
            "/userrole ID - статус роли\n"
            "/stats - cписок пользавателей \n"
            "/addbiz ID | Автоцентр Премиум | Иван Петров | Москва | Автосервис - создание бизнеса\n"
        )

    await message.answer(text)

@dp.message(Command("role"))
async def role(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

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

    if not await check_sub(message):
        await require_sub(message)
        return    

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

    if not await check_sub(message):
        await require_sub(message)
        return
    
        execute(
        "SELECT id, name FROM businesses ORDER BY id"
    )

    rows = cur.fetchall()

    if not rows:
        await message.answer("Список бизнесов пуст.")
        return

    text = "📋 Список бизнесов\n\n"

    for business_id, name in rows:
        text += f"🆔 {business_id} | {name}\n"

    await message.answer(text)

@dp.message(F.text == "📂 Категории")
async def menu_categories(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return    

    execute(
        """
        SELECT DISTINCT category
        FROM businesses
        WHERE category IS NOT NULL
        AND category != ''
        ORDER BY category
        """
    )

    rows = cur.fetchall()

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

    if not await check_sub(message):
        await require_sub(message)
        return    

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

@dp.message(Command("addbiz"))
async def addbiz(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return    

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

    if cur.fetchone():
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

        db.commit()

    await message.answer(
        f"✅ Бизнес создан.\n\n"
        f"ID: {business_id}\n"
        f"Название: {name}"
    )

@dp.message(Command("logs"))
async def logs(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return
    
    if not is_creator(message.from_user.id):
        await message.answer("Недостаточно прав.")
        return

        execute(
        """
        SELECT user_id, action, created_at
        FROM logs
        ORDER BY id DESC
        LIMIT 20
        """
    )

    rows = cur.fetchall()

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

    if not await check_sub(message):
        await require_sub(message)
        return
    
        execute(
        "SELECT * FROM roles"
    )

    rows = cur.fetchall()

    await message.answer(str(rows))
    
@dp.callback_query(F.data == "biz")
async def biz(callback: CallbackQuery):

    if not await check_sub(callback.message):
        await require_sub(callback.message)
        return

    await callback.answer()

    await bizlist(callback.message)

        execute(
        "SELECT id, name FROM businesses ORDER BY id"
    )

    rows = cur.fetchall()

    if not rows:
        await callback.message.answer(
            "Список бизнесов пуст."
        )
        return

    text = "📋 Список бизнесов\n\n"

    for business_id, name in rows:
        text += f"{business_id} - {name}\n"

    await callback.message.answer(text)


@dp.callback_query(F.data == "categories")
async def categories_btn(callback: CallbackQuery):

    if not await check_sub(callback.message):
        await require_sub(callback.message)
        return

    await callback.answer()

    await categories(callback.message)


@dp.callback_query(F.data == "help")
async def help_btn(callback: CallbackQuery):

    if not await check_sub(callback.message):
        await require_sub(callback.message)
        return

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
        BotCommand(command="admin", description="Список администрации"),
        BotCommand(command="rep", description="Проголосвать за репутацию"),
        BotCommand(command="topadmin", description="топ репутации администрации"),
        BotCommand(command="bug", description="Отправить предложение по улучшению"),
        BotCommand(command="bs", description="Посмотреть активные битвы семей"),
        BotCommand(command="profile", description="Посмотреть профиль"),
        BotCommand(command="zbt", description="Открыть список збт"),
        BotCommand(command="addzbt", description="Добавить пост о збт"),
        BotCommand(command="del", description="Удалить пост о збт"),
        BotCommand(command="repadm", description="Изменить репутацию ")
    ]

    await bot.set_my_commands(commands)

@dp.message(Command("clear"))
async def clear_chat(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return    

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

    if not await check_sub(message):
        await require_sub(message)
        return

    if get_role(message.from_user.id) < 2:
        await message.answer("Недостаточно прав.")
        return

    text = message.text.replace("/addadm", "", 1).strip()

    parts = [x.strip() for x in text.split("|")]

    if len(parts) != 4:
        await message.answer(
            "Пример:\n"
            "/addadm 1 | Willy | https://vk.com/willy | Главный администратор"
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

        execute(
        "SELECT id FROM admins WHERE id=%s",
        (admin_id,)
    )

    if cur.fetchone():
        await message.answer("Администратор с таким ID уже существует.")
        return

        execute(
        """
        INSERT INTO admins
        (id, nickname, vk, position, reputation)
        VALUES (%s, %s, %s, %s, 0)
        """,
        (
            admin_id,
            nickname,
            vk,
            position
        )
    )

        db.commit()

    add_log(
        message.from_user.id,
        f"Добавил администратора {nickname}"
    )

    await message.answer("✅ Администратор добавлен.")

@dp.message(Command("admins"))
async def admins(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

    await register_user(message)

        execute(
         """
        SELECT id, nickname, position
        FROM admins
        ORDER BY id
        """
    )

    rows = cur.fetchall()

    if not rows:
        await message.answer(
            "Список администрации пуст."
        )
        return

    text = "👮 Администрация Брянска\n\n"

    for admin_id, nickname, position in rows:
        text += (
            f"🆔 {admin_id} - "
            f"{nickname} - "
            f"{position}\n"
        )

    await message.answer(text)

@dp.message(Command("iadmin"))
async def iadmin(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

    await register_user(message)
    

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "Пример:\n/iadmin 1"
        )
        return

    try:
        admin_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом.")
        return

        execute("""
        SELECT id, nickname, vk, position, reputation
        FROM admins
        WHERE id=%s
    """, (admin_id,))

    admin = cur.fetchone()

    if not admin:
        await message.answer("Администратор не найден.")
        return

    admin_id, nickname, vk, position, reputation = admin

        execute("""
        SELECT id
        FROM admins
        ORDER BY reputation DESC, nickname
    """)

    rating = cur.fetchall()

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
        f"💼 Должность: {position}\n\n"
        f"⭐ Репутация: {reputation}\n"
        f"🏆 Место в рейтинге: {medal}\n\n"
        f"🔗 ВКонтакте:\n{vk}"
    )

    await message.answer(text)

@dp.message(Command("deladm"))
async def deladm(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

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

        execute(
        "SELECT nickname FROM admins WHERE id=%s",
        (admin_id,)
    )

    admin = cur.fetchone()

    if not admin:
        await message.answer("Администратор не найден.")
        return

    nickname = admin[0]

        execute(
        "DELETE FROM admins WHERE id=%s",
        (admin_id,)
    )

        db.commit()

    add_log(
        message.from_user.id,
        f"Удалил администратора {nickname}"
    )

    await message.answer(
        f"✅ Администратор {nickname} удалён."
    )

@dp.message(Command("dadm"))
async def dadm(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

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

        execute(
        "SELECT nickname FROM admins WHERE id=%s",
        (admin_id,)
    )

    admin = cur.fetchone()

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

        db.commit()

    add_log(
        message.from_user.id,
        f"Изменил должность {nickname} -> {new_position}"
    )

    await message.answer(
        "✅ Должность изменена."
    )

@dp.message(Command("repadm"))
async def repadm(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

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

        execute(
        "SELECT nickname FROM admins WHERE id=%s",
        (admin_id,)
    )

    admin = cur.fetchone()

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

        db.commit()

    add_log(
        message.from_user.id,
        f"Изменил репутацию {nickname} -> {reputation}"
    )

    await message.answer(
        f"✅ Репутация администратора {nickname} изменена на {reputation}."
    )
    
@dp.message(Command("rep"))
async def rep(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

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

        execute(
        "SELECT nickname FROM admins WHERE id=%s",
        (admin_id,)
    )

    admin = cur.fetchone()

    if not admin:
        await message.answer("Администратор не найден.")
        return

        execute(
        """
        SELECT vote
        FROM admin_votes
        WHERE user_id=%s AND admin_id=%s
        """,
        (
            message.from_user.id,
            admin_id
        )
    )

    if cur.fetchone():
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

        b.commit()

    await message.answer(
        "Спасибо за вашу оценку!"
    )

@dp.message(Command("topadmin"))
async def topadmin(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

        execute("""
        SELECT nickname, position, reputation
        FROM admins
        ORDER BY reputation DESC, nickname
        LIMIT 10
    """)

    rows = cur.fetchall()

    if not rows:
        await message.answer("Список администрации пуст.")
        return

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }

    text = "🏆 Топ по репутации администрации Брянска\n\n"

    for i, (nickname, position, reputation) in enumerate(rows, start=1):

        place = medals.get(i, f"🔹 {i} место")

        text += (
            f"{place}\n"
            f"👤 {nickname}\n"
            f"💼 {position}\n"
            f"⭐ Репутация: {reputation}\n\n"
        )

    await message.answer(text)

@dp.message(Command("bug"))
async def bug(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

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

        execute("SELECT user_id FROM users")

    for (user_id,) in cur.fetchall():
        try:
            await bot.send_message(user_id, text)
            users_sent += 1
        except:
            pass

        execute("SELECT chat_id FROM chats")

    for (chat_id,) in cur.fetchall():
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

        execute("SELECT COUNT(*) FROM users")
        users = cur.fetchone()[0]

        execute("SELECT COUNT(*) FROM chats")
         chats = cur.fetchone()[0]

        execute("SELECT COUNT(*) FROM businesses")
        businesses = cur.fetchone()[0]

        execute("SELECT COUNT(*) FROM admins")
        admins = cur.fetchone()[0]

    await message.answer(
        f"📊 Статистика бота\n\n"
        f"👤 Пользователей: {users}\n"
        f"👥 Групп: {chats}\n"
        f"🏢 Бизнесов: {businesses}\n"
        f"🛡 Администраторов: {admins}"
    )

from datetime import datetime

@dp.message(Command("addbs"))
async def addbs(message: Message):

    if get_role(message.from_user.id) < 1:
        return

    args = message.text.split()

    if len(args) != 3:
        await message.answer(
            "Пример:\n"
            "/addbs 17:00 1-5"
        )
        return

    end = args[1]
    location = args[2]

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

        db.commit()

    await message.answer("✅ Активная БС добавлена.")

from datetime import datetime

@dp.message(Command("bs"))
async def bs(message: Message):

        execute(
        "SELECT location, end_time FROM family_battle LIMIT 1"
    )

    row = cur.fetchone()

    if not row:
        await message.answer("Активных битв семей нет.")
        return

    location, end_time = row

    end = datetime.fromisoformat(end_time)

    if datetime.now() >= end:
       execute("DELETE FROM family_battle")
        db.commit()

        await message.answer("Активных битв семей нет.")
        return

    await message.answer(
        f"⚔ Активная битва семей\n\n"
        f"📍 Местоположение: /gps {location}\n"
        f"⏰ До окончания: {end.strftime('%H:%M')}"
    )

@dp.message(Command("delbs"))
async def delbs(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

    if get_role(message.from_user.id) < 1:
        await message.answer("Недостаточно прав.")
        return

        execute("DELETE FROM family_battle")
        db.commit()

    await message.answer("✅ Активная битва семей удалена.")

@dp.message(Command("profile"))
async def profile(message: Message):

    if not await check_sub(message):
        await require_sub(message)
        return

    args = message.text.split()

    # По умолчанию — свой профиль
    target_id = message.from_user.id

    # Если ответ на сообщение
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id

    # Если указан ID
    elif len(args) == 2:
        if args[1].isdigit():
            target_id = int(args[1])
        else:
            await message.answer("Укажите корректный ID.")
            return

        execute(
        """
        SELECT first_name, username, reg_date
        FROM users
        WHERE user_id=%s
        """,
        (target_id,)
    )

    user = cur.fetchone()

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

    if not await check_sub(message):
        await require_sub(message)
        return

    await register_user(message)
    
        execute("""
        SELECT chat_id, message_id
        FROM zbt_posts
        ORDER BY id
    """)

    posts = cur.fetchall()

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

        db.commit()

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

        db.commit()

    await message.answer("✅ Пост успешно сохранён.")


@dp.message()
async def save_chat(message: Message):

    if message.chat.type in ["group", "supergroup"]:

        execute(
            "INSERT OR IGNORE INTO chats(chat_id) VALUES(%s)",
            (message.chat.id,)
        )

        db.commit()

async def main():
    print("BOT STARTED")
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
