
import os
import sqlite3
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

TOKEN = "8568105038:AAHVmeBwvYrcTqwMPEokNWrLLt5Ka8XJs10"
ADMINS = [5639087435] 

bot = Bot(TOKEN)
dp = Dispatcher()

db = sqlite3.connect("database.db")
cur = db.cursor()

try:
    cur.execute(
        "ALTER TABLE businesses ADD COLUMN category TEXT"
    )
    db.commit()
except:
    pass

cur.execute("""
CREATE TABLE IF NOT EXISTS roles(
    user_id INTEGER PRIMARY KEY,
    role INTEGER DEFAULT 0
)
""")

db.commit()

def get_role(user_id):
    row = cur.execute(
        "SELECT role FROM roles WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if row:
        return row[0]

    return 0


def is_editor(user_id):
    return get_role(user_id) >= 1


def is_creator(user_id):
    return get_role(user_id) >= 2

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

@dp.message(Command("start"))
async def start(message: Message):

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Бизнесы")],
            [KeyboardButton(text="📂 Категории")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "Добро пожаловать!",
        reply_markup=kb
    )

@dp.message(Command("business"))
async def business(message: Message):
    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        await message.answer(
            "Пример:\n/business 15\nили\n/business Автосервис"
        )
        return

    search = args[1]

# Поиск по ID
if search.isdigit():

    cur.execute(
        """
        SELECT name, owner, location, photo_id, category
        FROM businesses
        WHERE id=?
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
cur.execute(
    """
    SELECT id, name
    FROM businesses
    WHERE name LIKE ?
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
cur.execute(
    """
    SELECT id, name
    FROM businesses
    WHERE category=?
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

await message.answer(
    "Бизнес или категория не найдены."
)

@dp.message(Command("bizlist"))
async def bizlist(message: Message):
    cur.execute(
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

@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id not in ADMINS:
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

    await message.answer("Админ-панель", reply_markup=kb)

@dp.message(F.text == "➕ Добавить бизнес")
async def add_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return

    await state.set_state(AddBusiness.id)
    await message.answer("Введите ID бизнеса")


@dp.message(AddBusiness.name)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddBusiness.owner)
    await message.answer("Введите владельца")

@dp.message(AddBusiness.id)
async def add_id(message: Message, state: FSMContext):
    try:
        business_id = int(message.text)
    except ValueError:
        await message.answer(
            "ID бизнеса должен быть числом.\nПример: 1"
        )
        return

    await state.update_data(id=business_id)
    await state.set_state(AddBusiness.name)
    await message.answer("Введите название бизнеса")

@dp.message(AddBusiness.owner)
async def add_owner(message: Message, state: FSMContext):
    await state.update_data(owner=message.text)
    await state.set_state(AddBusiness.category)
    await message.answer("Введите категорию")


@dp.message(AddBusiness.category)
async def add_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await state.set_state(AddBusiness.location)
    await message.answer("Введите адрес")


@dp.message(AddBusiness.location)
async def add_location(message: Message, state: FSMContext):
    data = await state.get_data()

    cur.execute(
        """
        INSERT INTO businesses
        (id, name, owner, category, location)
        VALUES (?, ?, ?, ?, ?)
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
    await state.set_state(ChangeOwner.business_id)
    await message.answer("Введите ID бизнеса")

@dp.message(ChangeOwner.business_id)
async def owner_bid(message: Message, state: FSMContext):
    await state.update_data(id=message.text)
    await state.set_state(ChangeOwner.owner)
    await message.answer("Введите нового владельца")

@dp.message(ChangeOwner.owner)
async def owner_save(message: Message, state: FSMContext):
    data = await state.get_data()

    cur.execute(
        "UPDATE businesses SET owner=? WHERE id=?",
        (message.text, data["id"])
    )
    db.commit()

    await state.clear()
    await message.answer("Владелец изменён.")

@dp.message(F.text == "📍 Изменить адрес")
async def location_start(message: Message, state: FSMContext):
    await state.set_state(ChangeLocation.business_id)
    await message.answer("Введите ID бизнеса")

@dp.message(ChangeLocation.business_id)
async def location_bid(message: Message, state: FSMContext):
    await state.update_data(id=message.text)
    await state.set_state(ChangeLocation.location)
    await message.answer("Введите новый адрес")

@dp.message(ChangeLocation.location)
async def location_save(message: Message, state: FSMContext):
    data = await state.get_data()

    cur.execute(
        "UPDATE businesses SET location=? WHERE id=?",
        (message.text, data["id"])
    )
    db.commit()

    await state.clear()
    await message.answer("Адрес обновлён.")

@dp.message(F.text == "📷 Добавить фото")
async def photo_start(message: Message, state: FSMContext):
    await state.set_state(UploadPhoto.business_id)
    await message.answer("Введите ID бизнеса")

@dp.message(UploadPhoto.business_id)
async def photo_bid(message: Message, state: FSMContext):
    await state.update_data(id=message.text)
    await state.set_state(UploadPhoto.photo)
    await message.answer("Отправьте фотографию")

@dp.message(UploadPhoto.photo, F.photo)
async def photo_save(message: Message, state: FSMContext):
    data = await state.get_data()

    photo_id = message.photo[-1].file_id

    cur.execute(
        "UPDATE businesses SET photo_id=? WHERE id=?",
        (photo_id, data["id"])
    )
    db.commit()

    await state.clear()
    await message.answer("Фото сохранено.")


@dp.message(Command("setrole"))
async def set_role(message: Message):
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

    cur.execute(
        """
        INSERT OR REPLACE INTO roles
        (user_id, role)
        VALUES (?,?)
        """,
        (user_id, role)
    )

    db.commit()

    await message.answer(
        f"Роль {role} выдана пользователю {user_id}"
    )

@dp.message(Command("cbiz"))
async def cbiz(message: Message):
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

    cur.execute(
        "UPDATE businesses SET category=? WHERE id=?",
        (category, business_id)
    )
    db.commit()

    await message.answer("Категория сохранена.")

@dp.message(Command("delcbiz"))
async def delcbiz(message: Message):
    if not is_editor(message.from_user.id):
        await message.answer("Недостаточно прав.")
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "Пример:\n/delcbiz 15"
        )
        return

    cur.execute(
        "UPDATE businesses SET category=NULL WHERE id=?",
        (args[1],)
    )

    db.commit()

    await message.answer(
        "Категория удалена."
    )

@dp.message(Command("nbiz"))
async def nbiz(message: Message):
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

    cur.execute(
        "SELECT id FROM businesses WHERE id=?",
        (business_id,)
    )

    if not cur.fetchone():
        await message.answer("Бизнес не найден.")
        return

    cur.execute(
        "UPDATE businesses SET name=? WHERE id=?",
        (new_name, business_id)
    )

    db.commit()

    await message.answer(
        "Название бизнеса изменено."
    )

@dp.message(Command("lbiz"))
async def lbiz(message: Message):
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

    cur.execute(
        "SELECT id FROM businesses WHERE id=?",
        (business_id,)
    )

    if not cur.fetchone():
        await message.answer("Бизнес не найден.")
        return

    cur.execute(
        "UPDATE businesses SET location=? WHERE id=?",
        (new_location, business_id)
    )

    db.commit()

    await message.answer(
        "Адрес бизнеса изменён."
    )

@dp.message(Command("delbiz"))
async def delbiz(message: Message):
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

    cur.execute(
        "SELECT id FROM businesses WHERE id=?",
        (business_id,)
    )

    if not cur.fetchone():
        await message.answer("Бизнес не найден.")
        return

    cur.execute(
        "DELETE FROM businesses WHERE id=?",
        (business_id,)
    )

    db.commit()

    await message.answer(
        "Бизнес удалён."
    )

@dp.message(Command("vbiz"))
async def vbiz(message: Message):
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

    cur.execute(
        "SELECT id FROM businesses WHERE id=?",
        (business_id,)
    )

    if not cur.fetchone():
        await message.answer("Бизнес не найден.")
        return

    cur.execute(
        "UPDATE businesses SET owner=? WHERE id=?",
        (new_owner, business_id)
    )

    db.commit()

    await message.answer(
        "Владелец бизнеса изменён."
    )

@dp.message(Command("fbiz"))
async def fbiz(message: Message, state: FSMContext):

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

    cur.execute(
        "SELECT id FROM businesses WHERE id=?",
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
    data = await state.get_data()

    photo_id = message.photo[-1].file_id

    cur.execute(
        "UPDATE businesses SET photo_id=? WHERE id=?",
        (photo_id, data["id"])
    )

    db.commit()

    await state.clear()

    await message.answer(
        "Фотография бизнеса обновлена."
    )

@dp.message(Command("categories"))
async def categories(message: Message):
    cur.execute(
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

    role = get_role(message.from_user.id)

    text = (
        "📖 Справка по командам\n\n"

        "👤 Пользователь:\n"
        "/business ID - информация о бизнесе\n"
        "/business Категория - поиск по категории\n"
        "/bizlist - список бизнесов\n"
        "/categories - список категорий\n"
        "/role - моя роль\n"
        "/support - справка\n"
    )

    if role >= 1:
        text += (
            "\n✏️ Редактор:\n"
            "/vbiz ID Новый владелец - изменение владельца\n"
            "/fbiz ID Фотография - изменение фотографии\n"
            "/cbiz ID Категория - изменение категории\n"
            "/delcbiz ID - удаление категории\n"
        )

    if role >= 2:
        text += (
            "\n👑 Создатель:\n"
            "/nbiz ID Новое название\n"
            "/lbiz ID Новый адрес\n"
            "/delbiz ID - удалить бизнес\n"
            "/userrole ID - статус роли\n"
            "/addbiz ID | Автоцентр Премиум | Иван Петров | Москва | Автосервис - создание бизнеса\n"
        )

    await message.answer(text)

@dp.message(Command("role"))
async def role(message: Message):

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
    cur.execute(
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

    cur.execute(
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

    cur.execute(
        "SELECT id FROM businesses WHERE id=?",
        (business_id,)
    )

    if cur.fetchone():
        await message.answer(
            "Бизнес с таким ID уже существует."
        )
        return

    cur.execute(
        """
        INSERT INTO businesses
        (id, name, owner, location, category)
        VALUES (?, ?, ?, ?, ?)
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

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    


