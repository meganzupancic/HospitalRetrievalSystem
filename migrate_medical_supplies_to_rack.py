"""
Migration script to import data from medical_supplies.db to rack.db

This script helps you migrate existing items from the old medical_supplies.db
to the new rack.db format.

Usage:
    python migrate_medical_supplies_to_rack.py
"""

import os
import sqlite3
import sys

# Paths
OLD_DB_PATH = os.path.join("raspi_system", "database", "medical_supplies.db")
NEW_DB_PATH = os.path.join("raspi_system", "database", "rack.db")


def get_conn(db_path):
    """Get a database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def migrate_data():
    """Migrate items from medical_supplies.db to rack.db."""

    if not os.path.exists(OLD_DB_PATH):
        print(f"❌ Old database not found at: {OLD_DB_PATH}")
        print("Nothing to migrate.")
        return

    if not os.path.exists(NEW_DB_PATH):
        print(f"❌ New database not found at: {NEW_DB_PATH}")
        print("Please run 'python -c \"from db import init_db; init_db()\"' first.")
        return

    print("🔄 Starting migration from medical_supplies.db to rack.db...")

    # Connect to both databases
    old_conn = get_conn(OLD_DB_PATH)
    new_conn = get_conn(NEW_DB_PATH)

    try:
        # Get all items from medical_supplies
        old_cursor = old_conn.cursor()
        old_cursor.execute(
            """
            SELECT item, rack, location, isCalled 
            FROM medical_supplies 
            WHERE rack > 0 AND location > 0
            ORDER BY item, rack, location
        """
        )

        old_items = old_cursor.fetchall()

        if not old_items:
            print("ℹ️  No items found in medical_supplies.db")
            return

        print(f"Found {len(old_items)} item placements to migrate\n")

        new_cursor = new_conn.cursor()
        migrated_count = 0
        skipped_count = 0

        for old_item in old_items:
            item_name = old_item["item"]
            rack_num = old_item["rack"]
            location_num = old_item["location"]
            is_called = old_item["isCalled"]

            print(
                f"  Processing: {item_name} → Rack {rack_num}, Location {location_num}"
            )

            # Check if rack exists in new database
            rack = new_cursor.execute(
                "SELECT id FROM racks WHERE id = ?", (rack_num,)
            ).fetchone()

            if not rack:
                print(f"    ⚠️  Rack {rack_num} doesn't exist in rack.db, skipping")
                skipped_count += 1
                continue

            # Find or create the item in the items table
            item = new_cursor.execute(
                "SELECT id FROM items WHERE label = ?", (item_name,)
            ).fetchone()

            if not item:
                # Create new item
                new_cursor.execute(
                    "INSERT INTO items(label, isCalled) VALUES(?, ?)",
                    (item_name, is_called),
                )
                item_id = new_cursor.lastrowid
                print(f"    ✅ Created new item with ID {item_id}")
            else:
                item_id = item["id"]
                # Update isCalled if this item was the most recently called
                if is_called:
                    new_cursor.execute(
                        "UPDATE items SET isCalled = ? WHERE id = ?",
                        (is_called, item_id),
                    )
                print(f"    ℹ️  Using existing item ID {item_id}")

            # In the old system, location is just a number
            # We need to map it to a slot_id in rack_slots
            # Assuming locations are numbered sequentially: location = (row * cols) + col + 1
            # For a 5x10 grid: location 1 = row 0, col 0; location 10 = row 0, col 9; location 11 = row 1, col 0

            # Get rack dimensions
            rack_info = new_cursor.execute(
                "SELECT rows, cols FROM racks WHERE id = ?", (rack_num,)
            ).fetchone()

            cols = rack_info["cols"]

            # Calculate row and col from location (1-indexed location to 0-indexed row/col)
            loc_index = location_num - 1
            row = loc_index // cols
            col = loc_index % cols

            # Find the slot_id
            slot = new_cursor.execute(
                "SELECT id FROM rack_slots WHERE rack_id = ? AND row = ? AND col = ?",
                (rack_num, row, col),
            ).fetchone()

            if not slot:
                print(f"    ⚠️  Slot at row {row}, col {col} doesn't exist, skipping")
                skipped_count += 1
                continue

            slot_id = slot["id"]

            # Check if this slot is already occupied
            existing = new_cursor.execute(
                "SELECT item_id FROM item_slots WHERE slot_id = ?", (slot_id,)
            ).fetchone()

            if existing:
                print(f"    ⚠️  Slot {slot_id} already occupied, skipping")
                skipped_count += 1
                continue

            # Place the item in the slot
            new_cursor.execute(
                """
                INSERT INTO item_slots(item_id, slot_id, item_label, rack_id) 
                VALUES(?, ?, ?, ?)
                """,
                (item_id, slot_id, item_name, rack_num),
            )

            print(f"    ✅ Placed in slot {slot_id} (row {row+1}, col {col+1})")
            migrated_count += 1

        # Commit changes
        new_conn.commit()

        print(f"\n{'='*60}")
        print("✅ Migration complete!")
        print(f"   Migrated: {migrated_count} items")
        print(f"   Skipped:  {skipped_count} items")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        new_conn.rollback()
        import traceback

        traceback.print_exc()

    finally:
        old_conn.close()
        new_conn.close()


def backup_databases():
    """Create backups of both databases before migration."""
    import shutil
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if os.path.exists(OLD_DB_PATH):
        backup_old = f"{OLD_DB_PATH}.backup_{timestamp}"
        shutil.copy2(OLD_DB_PATH, backup_old)
        print(f"📦 Backed up medical_supplies.db to: {backup_old}")

    if os.path.exists(NEW_DB_PATH):
        backup_new = f"{NEW_DB_PATH}.backup_{timestamp}"
        shutil.copy2(NEW_DB_PATH, backup_new)
        print(f"📦 Backed up rack.db to: {backup_new}")

    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Medical Supplies → Rack DB Migration Tool")
    print("=" * 60 + "\n")

    # Ask for confirmation
    response = input(
        "This will migrate data from medical_supplies.db to rack.db.\nContinue? (y/n): "
    )

    if response.lower() != "y":
        print("Migration cancelled.")
        sys.exit(0)

    print()
    backup_databases()
    migrate_data()

    print(
        "💡 Tip: You can now use the Flask UI at http://localhost:5000 to manage your rack!"
    )
    print("💡 The voice control system will use the same rack.db database.\n")
