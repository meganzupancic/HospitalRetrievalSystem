import json
import os

DB_PATH = "../raspi_system/database/medical_supplies.json"


def add_entry(item, rack, location):
    try:
        with open(DB_PATH, "r+") as f:
            data = json.load(f)
            new_entry = {"item": item, "rack": rack, "location": location}
            if new_entry not in data:
                data.append(new_entry)
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
                return True
        return False
    except Exception as e:
        print(f"Error updating database: {e}")
        return False
