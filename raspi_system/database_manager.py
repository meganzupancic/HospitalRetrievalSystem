import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "medical_supplies.db")
# print("Database path:", DB_PATH)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS medical_supplies (
            item TEXT UNIQUE,
            rack INTEGER,
            location INTEGER
        );
        """
    )
    conn.commit()
    conn.close()


def load_database_from_sqlite():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT item, rack, location FROM medical_supplies")
    rows = cursor.fetchall()
    conn.close()
    return [{"item": row[0], "rack": row[1], "location": row[2]} for row in rows]


def add_or_update_item(item, rack, location):
    print(f"🛠️ DB: {item} → Rack {rack}, Location {location}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO medical_supplies (item, rack, location)
        VALUES (?, ?, ?)
        ON CONFLICT(item) DO UPDATE SET rack=excluded.rack, location=excluded.location
        """,
        (item, rack, location),
    )
    conn.commit()
    conn.close()


def delete_item_by_name(item_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medical_supplies WHERE item = ?", (item_name,))
    conn.commit()
    conn.close()


def update_item_location(item_name, new_rack, new_location):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE medical_supplies SET rack = ?, location = ? WHERE item = ?",
        (new_rack, new_location, item_name),
    )
    conn.commit()
    conn.close()
