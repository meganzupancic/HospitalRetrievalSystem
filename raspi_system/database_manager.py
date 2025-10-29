import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "medical_supplies.db")
# print("Database path:", DB_PATH)


def init_db():
    """Initialize the database with a unique ID and support for duplicate items at different locations."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create current_items table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS current_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # First check if we need to migrate the old table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='medical_supplies'")
    old_table_exists = cursor.fetchone() is not None
    
    if old_table_exists:
        # Backup existing data
        cursor.execute("SELECT item, rack, location, isCalled FROM medical_supplies")
        old_data = cursor.fetchall()
        
        # Drop old table
        cursor.execute("DROP TABLE medical_supplies")
        print("Backed up old data and dropped old table")
    
    # Create new table with correct schema
    print("Creating medical_supplies table with new schema...")
    cursor.execute(
        """
        CREATE TABLE medical_supplies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            rack INTEGER NOT NULL,
            location INTEGER NOT NULL,
            isCalled INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    
    # Create index for item lookups
    cursor.execute(
        """
        CREATE INDEX idx_medical_supplies_item 
        ON medical_supplies(item);
        """
    )
    
    # Restore old data if we had any
    if old_table_exists and old_data:
        print("Restoring existing items...")
        cursor.executemany(
            """
            INSERT INTO medical_supplies (item, rack, location, isCalled)
            VALUES (?, ?, ?, ?)
            """,
            old_data
        )
    
    conn.commit()
    conn.close()


def load_database_from_sqlite():
    """Load all items from the database, including duplicates at different locations.
    Returns list sorted by creation time (newest first)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Cleanup any placeholder rows where rack or location is zero
    try:
        cursor.execute("DELETE FROM medical_supplies WHERE rack = 0 OR location = 0")
        conn.commit()
    except Exception:
        # If table doesn't exist yet or other issue, ignore
        pass
    
    try:
        # Get all fields including id and created_at, order by newest first
        cursor.execute("""
            SELECT id, item, rack, location, isCalled 
            FROM medical_supplies 
            WHERE rack > 0 OR location > 0
            ORDER BY created_at DESC, id DESC
        """)
        rows = cursor.fetchall()
        result = [
            {
                "id": row[0],
                "item": row[1],
                "rack": row[2],
                "location": row[3],
                "isCalled": bool(row[4])
            }
            for row in rows
        ]
    except Exception as e:
        print(f"Error loading database: {e}")
        result = []  # Return empty list on error
    
    conn.close()
    return result


def delete_zero_location_rows():
    """Remove any rows where rack==0 or location==0 (placeholder/unplaced entries)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM medical_supplies WHERE rack = 0 OR location = 0")
        conn.commit()
    except Exception as e:
        print(f"Error cleaning zero-location rows: {e}")
    finally:
        conn.close()


def update_item_by_id(row_id, new_rack, new_location):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE medical_supplies SET rack = ?, location = ? WHERE id = ?",
        (new_rack, new_location, row_id),
    )
    conn.commit()
    conn.close()
    try:
        delete_zero_location_rows()
    except Exception:
        pass


def add_or_update_item(item, rack, location, isCalled=False):
    print(f"🛠️ DB: {item} → Rack {rack}, Location {location}, isCalled={isCalled}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Always insert a new row - allow duplicates with different locations
    try:
        cursor.execute(
            """
            INSERT INTO medical_supplies (item, rack, location, isCalled)
            VALUES (?, ?, ?, ?)
            """,
            (item, rack, location, int(bool(isCalled))),
        )
        new_id = cursor.lastrowid
    except Exception as e:
        print(f"Error inserting item: {e}")
        cursor.execute(
            """
            INSERT INTO medical_supplies (item, rack, location)
            VALUES (?, ?, ?)
            """,
            (item, rack, location),
        )
        new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    try:
        delete_zero_location_rows()
    except Exception:
        pass
    return new_id


def delete_item_by_name(item_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medical_supplies WHERE item = ?", (item_name,))
    conn.commit()
    conn.close()


def delete_item_by_id(row_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medical_supplies WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()


def update_item_location(item_name, new_rack, new_location):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE medical_supplies SET rack = ?, location = ? WHERE item = ?",
        (new_rack, new_location, item_name),
    )
    conn.commit()
    conn.close()


def mark_item_as_most_recent(item_name):
    """Set isCalled = 1 for all entries matching item_name and set isCalled = 0 for all others.
    If item does not exist, creates a temporary entry that will be replaced when placed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # First reset all items to not called
        cursor.execute("UPDATE medical_supplies SET isCalled = 0")
        
        # Then set all matching items to called
        cursor.execute(
            "UPDATE medical_supplies SET isCalled = 1 WHERE item = ?",
            (item_name,)
        )
        
        # If no rows were updated, insert a temporary entry
        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO medical_supplies 
                (item, rack, location, isCalled) 
                VALUES (?, 0, 0, 1)
                """,
                (item_name,)
            )
        
        conn.commit()
    except Exception as e:
        print(f"Error marking items as called: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_item(item_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT item, rack, location, isCalled FROM medical_supplies WHERE item = ?", (item_name,))
        row = cursor.fetchone()
        if not row:
            return None
        return {"item": row[0], "rack": row[1], "location": row[2], "isCalled": bool(row[3])}
    except Exception as e:
        print(f"Error getting item: {e}")
        return None
    finally:
        conn.close()

def add_current_item(item_name):
    """Add an item to the current items list."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO current_items (item) VALUES (?)", (item_name,))
        conn.commit()
    except Exception as e:
        print(f"Error adding current item: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_current_items():
    """Get all items in the current items list."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT item FROM current_items ORDER BY created_at DESC")
        items = [row[0] for row in cursor.fetchall()]
        return items
    except Exception as e:
        print(f"Error getting current items: {e}")
        return []
    finally:
        conn.close()

def delete_current_item(item_name):
    """Delete an item from the current items list."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM current_items WHERE item=?", (item_name,))
        conn.commit()
    except Exception as e:
        print(f"Error deleting current item: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_distinct_items():
    """Return a list of distinct item names currently present in medical_supplies (non-empty)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Return union of items present in medical_supplies and current_items
        cursor.execute(
            """
            SELECT DISTINCT item FROM (
                SELECT item FROM medical_supplies WHERE item IS NOT NULL AND item <> ''
                UNION
                SELECT item FROM current_items WHERE item IS NOT NULL AND item <> ''
            ) ORDER BY item COLLATE NOCASE ASC
            """
        )
        items = [row[0] for row in cursor.fetchall()]
        return items
    except Exception as e:
        print(f"Error getting distinct items: {e}")
        return []
    finally:
        conn.close()
