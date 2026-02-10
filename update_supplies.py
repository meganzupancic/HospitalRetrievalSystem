#!/usr/bin/env python
"""Update needles and hand sanitizer to rack 2"""

import sys

sys.path.insert(0, '.')

from raspi_system.database_manager import (
    add_or_update_item,
    delete_item_by_name,
    load_database_from_sqlite,
)

# Load current database
print("Current database entries for needles and hand sanitizer:")
db = load_database_from_sqlite()
found_items = {}

for item in db:
    if 'needle' in item['item'].lower() or 'sanitizer' in item['item'].lower():
        key = item['item'].lower()
        if key not in found_items:
            found_items[key] = []
        found_items[key].append(item)
        print(f"  {item['item']} - Rack {item['rack']}, Location {item['location']}")

# Update needles and hand sanitizer to rack 2, location 1
items_to_update = ['needles', 'needle', 'hand sanitizer', 'sanitizer']
updated_count = 0

for item in db:
    item_lower = item['item'].lower()
    if any(search in item_lower for search in items_to_update):
        print(f"\nUpdating: {item['item']}")
        # Delete old entry
        delete_item_by_name(item['item'])
        # Add new entry with rack 2, location 1
        add_or_update_item(item['item'], rack=2, location=1, isCalled=item.get('isCalled', False))
        updated_count += 1
        print("  ✓ Updated to Rack 2, Location 1")

print(f"\n✅ Updated {updated_count} item(s)")

# Show updated database
print("\nUpdated database entries:")
updated_db = load_database_from_sqlite()
for item in updated_db:
    if 'needle' in item['item'].lower() or 'sanitizer' in item['item'].lower():
        print(f"  {item['item']} - Rack {item['rack']}, Location {item['location']}")
