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
    open=True
)

db = pool.getconn()
db.autocommit = True
cur = db.cursor()


def reconnect():
    global db, cur

    try:
        cur.close()
    except Exception:
        pass

    try:
        pool.putconn(db)
    except Exception:
        pass

    db = pool.getconn()
    db.autocommit = True
    cur = db.cursor()


class SafeCursor:
    def execute(self, query, params=None):
        global cur

        try:
            return cur.execute(query, params)
        except psycopg.OperationalError:
            reconnect()
            return cur.execute(query, params)

    def fetchone(self):
        return cur.fetchone()

    def fetchall(self):
        return cur.fetchall()

    def __getattr__(self, name):
        return getattr(cur, name)


cur = SafeCursor()


def close():
    global db

    try:
        pool.putconn(db)
    except Exception:
        pass

    pool.close()