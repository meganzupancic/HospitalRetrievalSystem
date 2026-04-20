"""
Database adapter for rack.db to work with raspi_system voice control.
Provides the same interface as database_manager.py but works with the rack/slot grid system.
"""

import os
import sqlite3

# Path to rack.db in the raspi_system/database folder
DB_PATH = os.path.join(os.path.dirname(__file__), "database", "rack.db")


def _lookup_terms(item_label):
    """Generate normalized lookup terms with simple singular/plural fallback."""
    base = str(item_label or "").strip()
    if not base:
        return []

    terms = [base]
    lower = base.lower()

    if lower.endswith("s") and len(base) > 1:
        terms.append(base[:-1])
    elif len(base) > 1:
        terms.append(base + "s")

    # Preserve order while removing duplicates (case-insensitive).
    seen = set()
    unique_terms = []
    for term in terms:
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_terms.append(term)
    return unique_terms


def get_conn():
    """Get a database connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def load_database_from_sqlite():
    """
    Load all items from rack.db and return them in the format expected by nlp_parser.

    Returns list of dicts with keys: id, item, rack, location, isCalled
    - item: the item label (searches tags and other_names too)
    - rack: the rack number (rack_id)
    - location: the slot_id where the item is located
    - isCalled: whether this item was recently called via voice
    """
    conn = get_conn()
    cursor = conn.cursor()

    try:
        # Join items with their slot placements
        # For items in multiple slots, we'll return multiple entries
        cursor.execute(
            """
            SELECT 
                i.id as item_id,
                i.label,
                i.tags,
                i.other_names,
                i.isCalled,
                islots.rack_id,
                islots.slot_id,
                rs.row,
                rs.col
            FROM items i
            JOIN item_slots islots ON i.id = islots.item_id
            JOIN rack_slots rs ON islots.slot_id = rs.id
            ORDER BY i.isCalled DESC, i.id DESC
        """
        )

        rows = cursor.fetchall()
        result = []

        for row in rows:
            # Main entry with label
            result.append(
                {
                    "id": row["item_id"],
                    "item": row["label"],
                    "source_type": "label",
                    "rack": row["rack_id"],
                    "location": row["slot_id"],
                    "isCalled": bool(row["isCalled"]),
                    "row": row["row"],
                    "col": row["col"],
                }
            )

            # Add entries for tags if present
            if row["tags"]:
                tags = [t.strip() for t in row["tags"].split(",") if t.strip()]
                for tag in tags:
                    result.append(
                        {
                            "id": row["item_id"],
                            "item": tag,
                            "source_type": "tag",
                            "rack": row["rack_id"],
                            "location": row["slot_id"],
                            "isCalled": bool(row["isCalled"]),
                            "row": row["row"],
                            "col": row["col"],
                        }
                    )

            # Add entries for other_names if present
            if row["other_names"]:
                other_names = [
                    n.strip() for n in row["other_names"].split(",") if n.strip()
                ]
                for name in other_names:
                    result.append(
                        {
                            "id": row["item_id"],
                            "item": name,
                            "source_type": "other_name",
                            "rack": row["rack_id"],
                            "location": row["slot_id"],
                            "isCalled": bool(row["isCalled"]),
                            "row": row["row"],
                            "col": row["col"],
                        }
                    )

        return result

    except Exception as e:
        print(f"Error loading rack database: {e}")
        return []
    finally:
        conn.close()


def mark_item_as_most_recent(item_label):
    """
    Mark an item as the most recently called (isCalled = 1).
    Resets all other items to isCalled = 0.

    Searches by label, tags, or other_names.
    """
    conn = get_conn()
    cursor = conn.cursor()

    try:
        # First, reset all items
        cursor.execute("UPDATE items SET isCalled = 0")

        # Find items matching label, tags, or other_names.
        # Use case-insensitive compare and singular/plural fallback.
        terms = _lookup_terms(item_label)
        total_updated = 0
        for term in terms:
            cursor.execute(
                """
                UPDATE items
                SET isCalled = 1
                WHERE LOWER(TRIM(label)) = LOWER(TRIM(?))
                   OR LOWER(COALESCE(tags, '')) LIKE '%' || LOWER(TRIM(?)) || '%'
                   OR LOWER(COALESCE(other_names, '')) LIKE '%' || LOWER(TRIM(?)) || '%'
            """,
                (term, term, term),
            )
            total_updated += cursor.rowcount

        conn.commit()

        if total_updated == 0:
            print(f"Warning: No item found matching '{item_label}'")

    except Exception as e:
        print(f"Error marking item as called: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_item(item_label):
    """
    Get the first item matching the label (or tags/other_names).
    Returns dict with keys: item, rack, location, isCalled, or None if not found.
    """
    conn = get_conn()
    cursor = conn.cursor()

    try:
        terms = _lookup_terms(item_label)
        for term in terms:
            cursor.execute(
                """
                SELECT
                    i.label as item,
                    islots.rack_id as rack,
                    islots.slot_id as location,
                    i.isCalled
                FROM items i
                JOIN item_slots islots ON i.id = islots.item_id
                WHERE LOWER(TRIM(i.label)) = LOWER(TRIM(?))
                   OR LOWER(COALESCE(i.tags, '')) LIKE '%' || LOWER(TRIM(?)) || '%'
                   OR LOWER(COALESCE(i.other_names, '')) LIKE '%' || LOWER(TRIM(?)) || '%'
                LIMIT 1
            """,
                (term, term, term),
            )

            row = cursor.fetchone()
            if row:
                return {
                    "item": row["item"],
                    "rack": row["rack"],
                    "location": row["location"],
                    "isCalled": bool(row["isCalled"]),
                }

        return None

    except Exception as e:
        print(f"Error getting item: {e}")
        return None
    finally:
        conn.close()


def get_distinct_items():
    """
    Return a list of all distinct item labels, tags, and other_names.
    This is used for voice recognition to know what items exist.
    """
    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT label, tags, other_names 
            FROM items 
            WHERE label IS NOT NULL AND label <> ''
        """
        )

        items_set = set()
        for row in cursor.fetchall():
            # Add the main label
            items_set.add(row["label"])

            # Add tags
            if row["tags"]:
                tags = [t.strip() for t in row["tags"].split(",") if t.strip()]
                items_set.update(tags)

            # Add other names
            if row["other_names"]:
                other_names = [
                    n.strip() for n in row["other_names"].split(",") if n.strip()
                ]
                items_set.update(other_names)

        return sorted(list(items_set), key=str.lower)

    except Exception as e:
        print(f"Error getting distinct items: {e}")
        return []
    finally:
        conn.close()


def add_or_update_item(item, rack, location, isCalled=False):
    """
    Legacy function for compatibility - not typically used with the rack UI.
    The rack UI uses the /place endpoint in app.py instead.
    """
    print(
        f"Note: add_or_update_item called with {item}, rack {rack}, location {location}"
    )
    print(
        "This function is for legacy compatibility. Use the Flask UI to manage rack items."
    )
    return None


def get_current_items():
    """
    Get all items that are currently placed (have slot assignments).
    Returns list of item labels.
    """
    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT DISTINCT i.label
            FROM items i
            JOIN item_slots islots ON i.id = islots.item_id
            ORDER BY i.label COLLATE NOCASE ASC
        """
        )

        return [row["label"] for row in cursor.fetchall()]

    except Exception as e:
        print(f"Error getting current items: {e}")
        return []
    finally:
        conn.close()


# Initialize the database if it doesn't exist
def init_db():
    """Initialize rack.db with the proper schema if needed."""
    # Import and call the main db.init_db()
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from db import init_db as main_init_db

    main_init_db()


# Auto-initialize on import
if not os.path.exists(DB_PATH):
    print(f"Initializing rack.db at {DB_PATH}")
    init_db()
