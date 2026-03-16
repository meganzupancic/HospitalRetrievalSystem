import os
import sqlite3
from pathlib import Path

# Support both local development and Raspberry Pi deployment
# If running from raspi_system directory, use database/rack.db
# Otherwise use rack.db in current directory
if os.path.exists(os.path.join(os.path.dirname(__file__), "raspi_system", "database")):
    DB_PATH = Path(os.path.dirname(__file__)) / "raspi_system" / "database" / "rack.db"
else:
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
        try:
            conn.execute("ALTER TABLE items ADD COLUMN isCalled INTEGER DEFAULT 0;")
        except sqlite3.OperationalError:
            pass

    # Ensure racks table has config column
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE racks ADD COLUMN config TEXT DEFAULT '4x4';")
        except sqlite3.OperationalError:
            pass

    # Seed one rack if none exists
    with get_conn() as conn:
        r = conn.execute("SELECT COUNT(*) AS c FROM racks").fetchone()["c"]
        if r == 0:
            for rack_num in range(1, 5):  # racks 1–4
                conn.execute(
                    "INSERT INTO racks(name, rows, cols) VALUES(?,?,?)",
                    (f"Rack {rack_num}", 4, 20),  # 4 rows (1 top + 3 bottom), 20 cols
                )
                rack_id = conn.execute(
                    "SELECT id FROM racks WHERE name=?", (f"Rack {rack_num}",)
                ).fetchone()["id"]

                for row in range(4):  # 4 rows
                    for col in range(20):  # 20 columns
                        conn.execute(
                            "INSERT INTO rack_slots(rack_id, row, col) VALUES(?,?,?)",
                            (rack_id, row, col),
                        )

    # Migrate existing racks to 20 columns if they still have 10
    with get_conn() as conn:
        racks = conn.execute("SELECT id, cols FROM racks").fetchall()
        for rack in racks:
            if rack["cols"] != 20:
                # Update rack to have 20 columns
                conn.execute("UPDATE racks SET cols = 20 WHERE id = ?", (rack["id"],))
                # Delete old slots
                conn.execute("DELETE FROM rack_slots WHERE rack_id = ?", (rack["id"],))
                # Create new slots with 20 columns and 4 rows
                for row in range(4):
                    for col in range(20):
                        conn.execute(
                            "INSERT INTO rack_slots(rack_id, row, col) VALUES(?,?,?)",
                            (rack["id"], row, col),
                        )
                conn.commit()

    # Create system_logs table if not exists
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS system_logs (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
                category  TEXT    NOT NULL,
                action    TEXT    NOT NULL,
                detail    TEXT
            );
        """
        )
        conn.commit()
