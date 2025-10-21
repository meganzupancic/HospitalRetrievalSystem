# database_manager.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "medical_supplies.db")
# print("Database path:", DB_PATH)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS medical_supplies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            rack INTEGER NOT NULL,
            location INTEGER NOT NULL
        )
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


def add_item(item, rack, location):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO medical_supplies (item, rack, location) VALUES (?, ?, ?)",
        (item, rack, location),
    )
    conn.commit()
    conn.close()


def delete_item_by_name(item_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Delete the item
    cursor.execute("DELETE FROM medical_supplies WHERE item = ?", (item_name,))
    conn.commit()

    # Create a temporary table without AUTOINCREMENT
    cursor.execute(
        """
        CREATE TEMPORARY TABLE temp_medical_supplies (
            id INTEGER,
            item TEXT NOT NULL,
            rack INTEGER NOT NULL,
            location INTEGER NOT NULL
        )
    """
    )

    # Copy remaining data into the temporary table with new sequential IDs
    cursor.execute("SELECT item, rack, location FROM medical_supplies")
    rows = cursor.fetchall()
    for new_id, row in enumerate(rows, start=1):
        cursor.execute(
            "INSERT INTO temp_medical_supplies (id, item, rack, location) VALUES (?, ?, ?, ?)",
            (new_id, row[0], row[1], row[2]),
        )

    # Clear the original table
    cursor.execute("DELETE FROM medical_supplies")

    # Insert renumbered data back into the original table
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='medical_supplies'")
    cursor.execute(
        "INSERT INTO medical_supplies (id, item, rack, location) SELECT id, item, rack, location FROM temp_medical_supplies"
    )

    conn.commit()
    conn.close()
