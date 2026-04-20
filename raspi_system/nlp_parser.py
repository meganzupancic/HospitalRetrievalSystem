# Extracts and normalizes keywords

import os
import re

from . import rack_database_adapter as database_manager
from .keyword_matcher import build_keyword_matcher
from .medical_abbreviations import normalize_abbreviations

_DEFAULT_FUZZY_THRESHOLD = 0.80


def _get_fuzzy_threshold():
    raw = os.getenv("NLP_FUZZY_THRESHOLD", str(_DEFAULT_FUZZY_THRESHOLD))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return _DEFAULT_FUZZY_THRESHOLD
    # Keep threshold in a sane range to avoid pathological matches.
    return max(0.60, min(0.99, value))


_REQUESTED_SIZE_RE = re.compile(r"\b(?P<value>\d+(?:\.\d+)?)\s*m(?:l|illiliters?)\b")
_ITEM_SIZE_RE = re.compile(
    r"\b(?P<low>\d+(?:\.\d+)?)(?:\s*[-–]\s*(?P<high>\d+(?:\.\d+)?))?\s*m(?:l|illiliters?)\b"
)


def _extract_requested_size(text):
    match = _REQUESTED_SIZE_RE.search((text or "").lower())
    if not match:
        return None

    try:
        return float(match.group("value"))
    except (TypeError, ValueError):
        return None


def _score_item_size(item_text, requested_size):
    if requested_size is None:
        return None

    match = _ITEM_SIZE_RE.search((item_text or "").lower())
    if not match:
        return None

    try:
        low = float(match.group("low"))
        high_text = match.group("high")
        high = float(high_text) if high_text is not None else low
    except (TypeError, ValueError):
        return None

    if low <= requested_size <= high:
        return 0.0

    return min(abs(requested_size - low), abs(requested_size - high))


def _prefer_size_specific_matches(text, result):
    lower_text = (text or "").lower()
    matched_term = str(result.get("matched_term", "")).lower()
    is_syringe_request = "syringe" in lower_text or "syringe" in matched_term
    if not is_syringe_request:
        return result

    requested_size = _extract_requested_size(text)
    if requested_size is None:
        return result

    matches = result.get("matches") or []
    if not matches:
        return result

    scored = []
    for match in matches:
        score = _score_item_size(match.get("item"), requested_size)
        if score is None:
            continue
        scored.append((score, match))

    if not scored:
        return result

    scored.sort(key=lambda item: (item[0], str(item[1].get("item", "")).lower()))
    best_score = scored[0][0]

    # Keep only the best matching size family, preserving duplicate rows for the same item.
    best_item_name = scored[0][1].get("item")
    best_id = scored[0][1].get("id")
    narrowed = [
        match
        for _, match in scored
        if match.get("id") == best_id
        and _score_item_size(match.get("item"), requested_size) == best_score
    ]

    if not narrowed:
        return result

    narrowed_result = result.copy()
    narrowed_result["matches"] = narrowed
    narrowed_result["item"] = best_item_name
    narrowed_result["matched_term"] = result.get("matched_term", best_item_name)
    return narrowed_result


def find_keyword(text, database, matcher=None):
    """Return a matched item dict and mark it as the most recent called item in the DB.

    The `database` argument is expected to be a list of dicts with at least the keys
    `item`, `rack`, and `location` (for example from `database_manager.load_database_from_sqlite()`).
    If `matcher` is supplied, it will be used directly. Otherwise a temporary matcher is built.
    """
    # Normalize medical abbreviations to improve matching accuracy
    normalized_text = normalize_abbreviations(text)

    if matcher is None:
        matcher = build_keyword_matcher(
            database, fuzzy_threshold=_get_fuzzy_threshold()
        )

    result = matcher.match(normalized_text)
    if not result:
        return None

    result = _prefer_size_specific_matches(normalized_text, result)

    # Mark the matched term as the most recent called in the persistent DB.
    # This lets tag matches update every item carrying that tag.
    try:
        database_manager.mark_item_as_most_recent(
            result.get("matched_term", result["item"])
        )
    except Exception:
        # Don't let DB errors break NLP flow
        pass

    # Ensure isCalled is present for downstream logic.
    if "isCalled" not in result:
        try:
            matches = result.get("matches") or []
            if matches:
                result["isCalled"] = any(
                    bool(match.get("isCalled", False)) for match in matches
                )
            else:
                db_item = database_manager.get_item(result["item"])
                result["isCalled"] = (
                    bool(db_item.get("isCalled", False)) if db_item else False
                )
        except Exception:
            result["isCalled"] = False

    return result
