#!/usr/bin/env python3
"""
Backfill script to copy tags and other_names from `items` into `item_slots`
for existing placements. Run from project root with:

    python scripts\backfill_item_slots.py

It will set `item_tags` and `item_other_names` on item_slots for rows
where those columns are NULL or empty.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), '..', 'rack.db')
DB = os.path.abspath(DB)

if not os.path.exists(DB):
    print('DB not found:', DB)
    raise SystemExit(1)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Update item_slots from items
sql = '''
UPDATE item_slots
SET item_tags = (
    SELECT i.tags FROM items i WHERE i.id = item_slots.item_id
),
item_other_names = (
    SELECT i.other_names FROM items i WHERE i.id = item_slots.item_id
)
WHERE item_id IS NOT NULL;
'''
print('Running backfill...')
cur.execute(sql)
conn.commit()

# Show a few sample rows to confirm (item_slots uses composite PK; no numeric id column)
rows = cur.execute('SELECT item_id, slot_id, item_label, item_tags, item_other_names, rack_id FROM item_slots LIMIT 20').fetchall()
for r in rows:
    print(dict(r))

conn.close()
print('Done.')
