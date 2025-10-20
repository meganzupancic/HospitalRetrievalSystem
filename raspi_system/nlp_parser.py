# Extracts and normalizes keywords


def find_keyword(text, database):
    text = text.lower()
    for entry in database:
        item = entry["item"].lower()
        if item in text:
            return f"Found '{entry['item']}' at Rack {entry['rack']}, Location {entry['location']}"
    return "No keyword found."
