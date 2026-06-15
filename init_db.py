import sqlite3

db = sqlite3.connect("database.db")
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

db.commit()
db.close()
print("database.db created")
