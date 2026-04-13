# Extracts and normalizes keywords

from . import rack_database_adapter as database_manager
from .keyword_matcher import build_keyword_matcher


def find_keyword(text, database, matcher=None):
    """Return a matched item dict and mark it as the most recent called item in the DB.

    The `database` argument is expected to be a list of dicts with at least the keys
    `item`, `rack`, and `location` (for example from `database_manager.load_database_from_sqlite()`).
    If `matcher` is supplied, it will be used directly. Otherwise a temporary matcher is built.
    """
    if matcher is None:
        matcher = build_keyword_matcher(database)

    result = matcher.match(text)
    if not result:
        return None

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
