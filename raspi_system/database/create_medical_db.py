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

    # Insert items exactly as requested by the user.
    # Requested mapping:
    # - Thermometer: locations 1,2
    # - Needles: location 3
    # - Hand Sanitizer: locations 4,5,6
    # - Adhesive Tape: locations 7,8,9,10
    # - Syringe: locations 11,12

    items = []
    # Thermometer (1,2)
    items += [("Thermometer", 1, s) for s in (1, 2)]
    # Needles (3)
    items += [("Needles", 1, 3)]
    # Hand Sanitizer (4,5,6)
    items += [("Hand Sanitizer", 1, s) for s in (4, 5, 6)]
    # Adhesive Tape (7,8,9,10)
    items += [("Adhesive Tape", 1, s) for s in (7, 8, 9, 10)]
    # Syringe (11,12)
    items += [("Syringe", 1, s) for s in (11, 12)]

    cur.executemany(
        "INSERT INTO medical_supplies (item, rack, location) VALUES (?,?,?)",
        items,
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
