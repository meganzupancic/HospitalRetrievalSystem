# Extracts and normalizes keywords

from . import database_manager


def find_keyword(text, database):
    """Return the matched item dict and mark it as the most recent called item in the DB.

    The `database` argument is expected to be a list of dicts with at least the keys
    `item`, `rack`, and `location` (for example from `database_manager.load_database_from_sqlite()`).
    """
    text = text.lower()
    for entry in database:
        item = entry["item"].lower()
        if item in text:
            # Mark this item as the most recent called in the persistent DB
            try:
                database_manager.mark_item_as_most_recent(entry["item"])
            except Exception:
                # Don't let DB errors break NLP flow
                pass

            # Return entry including isCalled flag if present
            result = {
                "item": entry["item"],
                "rack": entry.get("rack", 0),
                "location": entry.get("location", 0),
            }
            # include isCalled if the database entry contains it
            if "isCalled" in entry:
                result["isCalled"] = bool(entry["isCalled"])
            else:
                # best-effort: query DB for this item
                try:
                    db_item = database_manager.get_item(entry["item"])
                    result["isCalled"] = bool(db_item.get("isCalled", False)) if db_item else False
                except Exception:
                    result["isCalled"] = False

            return result
    return None
