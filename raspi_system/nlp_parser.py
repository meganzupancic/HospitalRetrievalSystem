# Extracts and normalizes keywords


def find_keyword(text, database):
    text = text.lower()
    for entry in database:
        item = entry["item"].lower()
        if item in text:
            return {
                "item": entry["item"],
                "rack": entry["rack"],
                "location": entry["location"],
            }
    return None
