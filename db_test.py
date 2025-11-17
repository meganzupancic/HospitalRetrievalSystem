from db import get_conn

conn = get_conn()
cur = conn.execute("SELECT * FROM item_slots")
rows = cur.fetchall()
for row in rows:
    print(dict(row))
conn.close()
