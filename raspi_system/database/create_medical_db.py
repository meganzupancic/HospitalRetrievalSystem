#!/usr/bin/env python3
import sqlite3
from pathlib import Path


def main():
    # Use the canonical filename expected by the app (medical_supplies.db)
    db_path = Path(__file__).parent / "medical_supplies.db"
    # Remove existing DB so this is idempotent for this script
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create table using the schema expected by database_manager.py
    cur.execute(
        """
        CREATE TABLE medical_supplies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            rack INTEGER NOT NULL,
            location INTEGER NOT NULL,
            isCalled INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Base single-slot items (item, rack, location)
    items = [
        ("Bandage", 1, 1),
        ("Syringe", 1, 2),
        ("Gauze", 1, 3),
        ("IV Kit", 1, 4),
        ("Adhesive Tape", 1, 5),
    ]

    # Insert base items
    cur.executemany(
        "INSERT INTO medical_supplies (item, rack, location) VALUES (?,?,?)",
        items,
    )

    # Add multi-slot items by inserting one row per occupied slot.
    # Gloves will occupy slots 6-8 (3 slots)
    gloves_slots = [("Gloves", 1, s) for s in range(6, 9)]
    # Thermometer will occupy slots 9-10 (2 slots)
    thermometer_slots = [("Thermometer", 1, s) for s in range(9, 11)]

    cur.executemany(
        "INSERT INTO medical_supplies (item, rack, location) VALUES (?,?,?)",
        gloves_slots + thermometer_slots,
    )

    conn.commit()

    print(f"Created DB: {db_path.resolve()}")
    print("Rows:")
    for row in cur.execute(
        "SELECT item, rack, location FROM medical_supplies ORDER BY location"
    ):
        print(row)

    conn.close()


if __name__ == "__main__":
    main()
