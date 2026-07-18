from database import cur

sql = """
CREATE TABLE IF NOT EXISTS logs(
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    action TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

try:
    cur.execute(sql)
    print("OK")
except Exception as e:
    print(e)