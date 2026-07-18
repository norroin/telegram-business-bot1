import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

print("Подключение...")

conn = psycopg.connect(
    DATABASE_URL,
    autocommit=True
)

print("Соединение установлено")

with conn.cursor() as cur:

    cur.execute("SELECT 1")
    print("SELECT OK")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS test_table(
            id BIGSERIAL PRIMARY KEY
        )
    """)

    print("CREATE OK")

conn.close()

print("Готово")