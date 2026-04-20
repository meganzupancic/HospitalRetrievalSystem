"""Medical abbreviations and unit mappings for voice recognition.

Maps common medical abbreviations to their full forms to improve matching accuracy.
"""

# Common medical abbreviations and their expansions
ABBREVIATION_MAP = {
    # Volume measurements
    "ml": "milliliter",
    "mls": "milliliters",
    "cc": "cubic centimeter",
    "ccs": "cubic centimeters",
    "l": "liter",
    "ls": "liters",
    "ul": "microliter",
    "uls": "microliters",
    "µl": "microliter",
    "µls": "microliters",
    # Weight measurements
    "mg": "milligram",
    "mgs": "milligrams",
    "g": "gram",
    "gs": "grams",
    "kg": "kilogram",
    "kgs": "kilograms",
    "ug": "microgram",
    "ugs": "micrograms",
    "µg": "microgram",
    "µgs": "micrograms",
    # Common medical items
    "iv": "intravenous",
    "ivs": "intravenous",
    "ekg": "electrocardiogram",
    "ecg": "electrocardiogram",
    "cpr": "cardiopulmonary resuscitation",
    "icu": "intensive care unit",
    "er": "emergency room",
    "ed": "erectile dysfunction",
    "pid": "pelvic inflammatory disease",
    "std": "sexually transmitted disease",
    "uti": "urinary tract infection",
    "aids": "acquired immunodeficiency syndrome",
    "hiv": "human immunodeficiency virus",
    "cough": "cough",
    "covid": "covid",
    # Supplies and equipment
    "npo": "nothing by mouth",
    "po": "by mouth",
    "npr": "nothing per rectum",
    "pr": "per rectum",
    "pv": "per vagina",
    "sc": "subcutaneous",
    "im": "intramuscular",
    "id": "intradermal",
    "bp": "blood pressure",
    "hr": "heart rate",
    "rr": "respiratory rate",
    "temp": "temperature",
    "o2": "oxygen",
    # Specific to syringes and needles
    "syringe": "syringe",
    "syringes": "syringes",
    "needle": "needle",
    "needles": "needles",
    "gauge": "gauge",
    # Common abbreviations
    "pt": "patient",
    "pts": "patients",
    "doc": "doctor",
    "rx": "prescription",
    "tx": "treatment",
    "dx": "diagnosis",
    "hx": "history",
    "sx": "symptom",
}

# Phrase-level replacements (longer phrases to expand)
PHRASE_REPLACEMENTS = {
    "one milliliter": "1 mL",
    "1 milliliter": "1 mL",
    "2 milliliter": "2 mL",
    "3 milliliter": "3 mL",
    "5 milliliter": "5 mL",
    "10 milliliter": "10 mL",
    "20 milliliter": "20 mL",
    "50 milliliter": "50 mL",
    "100 milliliter": "100 mL",
    "two milliliter": "2 mL",
    "three milliliter": "3 mL",
    "five milliliter": "5 mL",
    "ten milliliter": "10 mL",
    "twenty milliliter": "20 mL",
    "fifty milliliter": "50 mL",
    "hundred milliliter": "100 mL",
    "2 milliliters": "2 mL",
    "3 milliliters": "3 mL",
    "5 milliliters": "5 mL",
    "10 milliliters": "10 mL",
    "20 milliliters": "20 mL",
    "50 milliliters": "50 mL",
    "100 milliliters": "100 mL",
}

# Spoken number words that commonly appear in supply requests.
NUMBER_WORD_REPLACEMENTS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",
    "twenty": "20",
    "fifty": "50",
    "hundred": "100",
}

# Common STT mishearings - phonetic errors that Vosk makes
# Maps words that sound similar but are misheard to their correct forms
PHONETIC_CORRECTIONS = {
    # "milliliter" mishearings - sounds like "mil leader", "mil peter", "mill letter", etc
    "mil leader": "milliliter",
    "mil peter": "milliliter",
    "mill letter": "milliliter",
    "mil liter": "milliliter",
    "ml leader": "milliliter",
    "ml peter": "milliliter",
    "mill peter": "milliliter",
    # Common medical misheard terms
    "cc": "cubic centimeter",
    "see see": "cubic centimeter",
    "inject": "injection",
    "injected": "injection",
    "band aid": "bandage",
    "band-aid": "bandage",
    "gauze": "gauze",
    "glove": "gloves",
    "mask": "face mask",
    "scissor": "scissors",
    "thermometer": "thermometer",
    "temp": "thermometer",
    # Syringe size variations (handle common mishearings)
    "1ml": "1 milliliter syringe",
    "3ml": "3 milliliter syringe",
    "5ml": "5 milliliter syringe",
    "10ml": "10 milliliter syringe",
    "20ml": "20 milliliter syringe",
    "1mm": "1 milliliter syringe",
    "3mm": "3 milliliter syringe",
    "5mm": "5 milliliter syringe",
    "10mm": "10 milliliter syringe",
}

# Common medical supply aliases - map variations to standard items
SUPPLY_ALIASES = {
    "band aid": ["bandage", "bandaid", "band-aid", "adhesive bandage", "plaster"],
    "gauze pads": ["gauze", "gauze pad", "sterile gauze", "gaze"],
    "antiseptic wipes": [
        "antiseptic wipe",
        "antibiotic wipe",
        "alcohol wipe",
        "disinfectant wipe",
    ],
    "latex gloves": [
        "gloves",
        "latex glove",
        "rubber gloves",
        "surgical gloves",
        "nitrile gloves",
        "glove",
    ],
    "thermometer": ["temp", "temperature", "temp meter"],
    "alcohol swabs": [
        "alcohol swab",
        "alcohol prep",
        "alcohol pads",
        "rubbing alcohol",
    ],
    "medical tape": ["medical tape", "tape", "surgical tape", "adhesive tape"],
    "syringes": [
        "syringe",
        "needle",
        "shot",
        "injection",
        "1 ml syringe",
        "3 ml syringe",
        "5 ml syringe",
        "10 ml syringe",
        "20 ml syringe",
        "1 mil leader syringe",
        "1 mil peter syringe",
        "1 mill letter syringe",
        "3 mil leader syringe",
        "3 mil peter syringe",
        "3 mill letter syringe",
        "5 mil leader syringe",
        "5 mil peter syringe",
        "5 mill letter syringe",
        "10 mil leader syringe",
        "10 mil peter syringe",
        "10 mill letter syringe",
        "20 mil leader syringe",
        "20 mil peter syringe",
        "20 mill letter syringe",
    ],
    "face masks": ["mask", "face mask", "surgical mask", "n95"],
    "oxygen masks": [
        "oxygen mask",
        "oxygen masks",
        "o2 mask",
        "o2 masks",
        "oxygen face mask",
    ],
    "scissors": ["scissor", "surgical scissors", "bandage scissors"],
}


def normalize_abbreviations(text: str) -> str:
    """Expand common medical abbreviations and phonetic mishearings in text.

    Args:
        text: Input text potentially containing abbreviations

    Returns:
        Text with abbreviations expanded to full words
    """
    if not text:
        return text

    text = text.lower()

    # First handle phonetic corrections (STT mishearings)
    # These must be done as whole phrases to catch mishearings like "mil leader"
    for mishearing, correction in PHONETIC_CORRECTIONS.items():
        text = text.replace(mishearing, correction)

    # Convert spoken number words to digits when they appear as standalone tokens.
    words = text.split()
    words = [NUMBER_WORD_REPLACEMENTS.get(word, word) for word in words]
    text = " ".join(words)

    # Then handle phrase-level replacements
    for phrase, replacement in PHRASE_REPLACEMENTS.items():
        text = text.replace(phrase, replacement)

    # Handle abbreviations with word boundaries
    words = text.split()
    normalized_words = []

    for word in words:
        # Remove punctuation while keeping the word
        clean_word = word.strip(".,!?;:")

        # Check if word matches an abbreviation
        if clean_word in ABBREVIATION_MAP:
            normalized_words.append(ABBREVIATION_MAP[clean_word])
            # Re-add punctuation if present
            if word != clean_word:
                normalized_words[-1] += word[len(clean_word) :]
        else:
            normalized_words.append(word)

    return " ".join(normalized_words)


def get_supply_aliases(item: str) -> list:
    """Get all known aliases for a medical supply item.

    Args:
        item: The canonical item name

    Returns:
        List of aliases for the item, or empty list if not found
    """
    return SUPPLY_ALIASES.get(item.lower(), [])


def expand_database_with_aliases(database: list) -> list:
    """Expand database entries with aliases for better matching.

    Args:
        database: List of item dicts with 'item', 'rack', 'location' keys

    Returns:
        Expanded database with alias entries
    """
    expanded = database.copy()

    for entry in database:
        item_name = (entry.get("item") or "").lower()
        aliases = get_supply_aliases(item_name)

        for alias in aliases:
            alias_entry = entry.copy()
            alias_entry["item"] = alias
            alias_entry["source_type"] = "alias"
            expanded.append(alias_entry)

    return expanded
