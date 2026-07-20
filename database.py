import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def connect():
    conn = psycopg.connect(DATABASE_URL)
    conn.autocommit = True
    return conn


db = connect()
cur = db.cursor()


def reconnect():
    global db, cur

    try:
        cur.close()
    except:
        pass

    try:
        db.close()
    except:
        pass

    db = connect()
    cur = db.cursor()


def execute(query, params=None):
    global db, cur

    try:
        return cur.execute(query, params or ())
    except psycopg.OperationalError:
        reconnect()
        return cur.execute(query, params or ())