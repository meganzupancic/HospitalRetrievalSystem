import sqlite3
from pathlib import Path

DB_PATH = Path("rack.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    # Run the base schema from models.sql
    with get_conn() as conn, open("models.sql", "r") as f:
        conn.executescript(f.read())

    # Ensure item_slots has item_label column
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE item_slots ADD COLUMN item_label TEXT;")
        except sqlite3.OperationalError:
            # Column already exists, ignore
            pass
    
    # Ensure item_slots has item_tags and item_other_names columns (store snapshot of item metadata per placement)
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE item_slots ADD COLUMN item_tags TEXT;")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE item_slots ADD COLUMN item_other_names TEXT;")
        except sqlite3.OperationalError:
            pass

    # Ensure items table has tags and other_names columns
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE items ADD COLUMN tags TEXT;")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE items ADD COLUMN other_names TEXT;")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE items ADD COLUMN color TEXT;")
        except sqlite3.OperationalError:
            pass

    # Seed one rack if none exists
    with get_conn() as conn:
        r = conn.execute("SELECT COUNT(*) AS c FROM racks").fetchone()["c"]
        if r == 0:
            for rack_num in range(1, 5):  # racks 1–4
                conn.execute(
                    "INSERT INTO racks(name, rows, cols) VALUES(?,?,?)",
                    (f"Rack {rack_num}", 5, 10),  # 5 rows, 10 cols
                )
                rack_id = conn.execute(
                    "SELECT id FROM racks WHERE name=?", (f"Rack {rack_num}",)
                ).fetchone()["id"]

                for row in range(5):  # 5 rows
                    for col in range(10):  # 10 columns
                        conn.execute(
                            "INSERT INTO rack_slots(rack_id, row, col) VALUES(?,?,?)",
                            (rack_id, row, col),
                        )
