from database import cur, db

tables = [

"""
CREATE TABLE IF NOT EXISTS users(
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    reg_date TEXT
)
""",

"""
CREATE TABLE IF NOT EXISTS roles(
    user_id BIGINT PRIMARY KEY,
    role INTEGER DEFAULT 0
)
""",

"""
CREATE TABLE IF NOT EXISTS chats(
    chat_id BIGINT PRIMARY KEY
)
""",

"""
CREATE TABLE IF NOT EXISTS businesses(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    location TEXT NOT NULL,
    photo_id TEXT,
    category TEXT
)
""",

"""
CREATE TABLE IF NOT EXISTS logs(
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    action TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""",

"""
CREATE TABLE IF NOT EXISTS admin_votes(
    user_id BIGINT,
    admin_id BIGINT,
    vote INTEGER,
    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, admin_id)
)
""",

"""
CREATE TABLE IF NOT EXISTS family_battle(
    id SERIAL PRIMARY KEY,
    location TEXT,
    end_time TIMESTAMP
)
""",

"""
CREATE TABLE IF NOT EXISTS zbt_posts(
    id SERIAL PRIMARY KEY,
    chat_id BIGINT,
    message_id BIGINT
)
"""

]

for table in tables:
    cur.execute(table)

db.commit()

print("✅ PostgreSQL tables created.")