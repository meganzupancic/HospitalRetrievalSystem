#!/usr/bin/env python3
"""
Simple migration script to add `tags`, `other_names`, and `color` columns
to the `items` table in `rack.db` if they are missing.

Run from project root with:

    python scripts\migrate_add_item_columns.py

It prints the `PRAGMA table_info(items)` before and after.
"""
import os
import sqlite3

DB = os.path.join(os.path.dirname(__file__), "..", "rack.db")
DB = os.path.abspath(DB)

ALTERS = [
    ("tags", "TEXT"),
    ("other_names", "TEXT"),
    ("color", "TEXT"),
]


def table_info(conn, table="items"):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return list(cur.fetchall())


def column_exists(info_rows, colname):
    return any(r[1] == colname for r in info_rows)


def main():
    if not os.path.exists(DB):
        print(f"DB not found at {DB}. Make sure the path is correct and the DB exists.")
        return

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    print("Before:")
    before = table_info(conn)
    for r in before:
        print(r)

    for col, ctype in ALTERS:
        if not column_exists(before, col):
            sql = f"ALTER TABLE items ADD COLUMN {col} {ctype};"
            print("Executing:", sql)
            conn.execute(sql)
        else:
            print(f"Column '{col}' already exists, skipping")

    conn.commit()

    print("\nAfter:")
    after = table_info(conn)
    for r in after:
        print(r)

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
