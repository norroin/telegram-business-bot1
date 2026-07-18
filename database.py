import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

db = psycopg.connect(DATABASE_URL)
db.autocommit = True

cur = db.cursor()


def execute(query, params=None):
    cur.execute(query, params or ())
    return cur


def commit():
    pass


def close():
    cur.close()
    db.close()