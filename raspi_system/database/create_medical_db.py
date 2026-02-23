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
    # - Thermometer: rack 1, locations 2, 8
    # - Adhesive Tape: rack 2, locations 9, 20
    # - Syringe: rack 3, location 1
    # - Hand Sanitizer: rack 4, location 15

    items = []
    # Thermometer: rack 1, locations 2 and 8
    items += [("Thermometer", 1, s) for s in (2, 8)]
    # Adhesive Tape: rack 2, locations 9 and 20
    items += [("Adhesive Tape", 2, s) for s in (9, 20)]
    # Syringe: rack 3, location 1
    items += [("Syringe", 3, 1)]
    # Hand Sanitizer: rack 4, location 15
    items += [("Hand Sanitizer", 4, 15)]

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
