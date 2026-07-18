from database import cur

cur.execute("SELECT version();")

print(cur.fetchone())