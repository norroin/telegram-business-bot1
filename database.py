import os
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL не найден")

db = psycopg.connect(DATABASE_URL)
db.autocommit = True

cur = db.cursor()
