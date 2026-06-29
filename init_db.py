import sqlite3

db = sqlite3.connect("/data/database.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS businesses(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    location TEXT NOT NULL,
    photo_id TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS roles(
    user_id INTEGER PRIMARY KEY,
    role INTEGER DEFAULT 0
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS admins(
    id INTEGER PRIMARY KEY,
    nickname TEXT NOT NULL,
    vk TEXT,
    position TEXT,
    reputation INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS admin_votes(
    user_id INTEGER,
    admin_id INTEGER,
    vote INTEGER,
    PRIMARY KEY(user_id, admin_id)
)
""")

db.commit()
db.close()
print("database.db created")

