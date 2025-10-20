# database_manager.py

import json


def load_database_from_json(file_path):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        return data["medical_supplies"]
    except Exception as e:
        print(f"Error loading database: {e}")
        return []
