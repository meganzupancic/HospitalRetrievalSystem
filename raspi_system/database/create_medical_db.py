#!/usr/bin/env python3
import sqlite3
import random
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
    # Requested items:
    # Sterile gloves
    # Non‑sterile exam gloves
    # Surgical masks
    # N95 respirators
    # Isolation gowns
    # Face shields
    # Surgical caps
    # Shoe covers
    # Alcohol prep pads
    # Hand sanitizer
    # Sterile gauze pads
    # Gauze rolls
    # ABD pads
    # Transparent dressings
    # Foam dressings
    # Hydrocolloid dressings
    # Adhesive bandages
    # Medical tape
    # Suture kits
    # Staple removal kits
    # IV catheters
    # IV tubing sets
    # IV extension sets
    # Saline flush syringes
    # Heparin flush syringes
    # IV start kits
    # Tourniquets
    # Needles
    # Syringes
    # Chlorhexidine swabs
    # Normal saline bags
    # Lactated Ringer’s bags
    # Dextrose solution bags
    # Blood collection tubes
    # Vacutainer holders
    # Butterfly needles
    # Specimen labels
    # Urine collection cups
    # Stool specimen containers
    # Biohazard bags
    # Blood pressure cuffs
    # Spare stethoscopes
    # Pulse oximeter probes
    # Thermometer probe covers
    # Suction canisters
    # Yankauer suction tips
    # Nebulizer kits
    # Oxygen nasal cannulas
    # Oxygen masks
    # Bedpans

    # then assign them to random racks (1-4) and locations (1-20). Some items can have multiple locations

    requested_items = [
        "Sterile gloves",
        "Non-sterile exam gloves",
        "Surgical masks",
        "N95 respirators",
        "Isolation gowns",
        "Face shields",
        "Surgical caps",
        "Shoe covers",
        "Alcohol prep pads",
        "Hand sanitizer",
        "Sterile gauze pads",
        "Gauze rolls",
        "ABD pads",
        "Transparent dressings",
        "Foam dressings",
        "Hydrocolloid dressings",
        "Adhesive bandages",
        "Medical tape",
        "Suture kits",
        "Staple removal kits",
        "IV catheters",
        "IV tubing sets",
        "IV extension sets",
        "Saline flush syringes",
        "Heparin flush syringes",
        "IV start kits",
        "Tourniquets",
        "Needles",
        "Syringes",
        "Chlorhexidine swabs",
        "Normal saline bags",
        "Lactated Ringer's bags",
        "Dextrose solution bags",
        "Blood collection tubes",
        "Vacutainer holders",
        "Butterfly needles",
        "Specimen labels",
        "Urine collection cups",
        "Stool specimen containers",
        "Biohazard bags",
        "Blood pressure cuffs",
        "Spare stethoscopes",
        "Pulse oximeter probes",
        "Thermometer probe covers",
        "Suction canisters",
        "Yankauer suction tips",
        "Nebulizer kits",
        "Oxygen nasal cannulas",
        "Oxygen masks",
        "Bedpans",
    ]

    items = []
    for item in requested_items:
        # Assign to random rack (1-4) and location (1-20)
        rack = random.randint(1, 4)
        num_locations = random.randint(1, 3)  # Some items have multiple locations
        locations = random.sample(range(1, 21), num_locations)
        for location in locations:
            items.append((item, rack, location))

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
