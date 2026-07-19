import os
import psycopg
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=5,
)

db = None
cur = None


def reconnect():
    global db, cur

    if db:
        try:
            pool.putconn(db)
        except:
            pass

    db = pool.getconn()
    db.autocommit = True
    cur = db.cursor()


reconnect()


def execute(query, params=None):
    global db, cur

    try:
        cur.execute(query, params or ())
    except psycopg.OperationalError:
        reconnect()
        cur.execute(query, params or ())

    return cur


class SafeCursor:
    def execute(self, query, params=None):
        return execute(query, params)

    def fetchone(self):
        return cur.fetchone()

    def fetchall(self):
        return cur.fetchall()


cur = SafeCursor()


def commit():
    pass