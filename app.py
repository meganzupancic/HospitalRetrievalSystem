# app.py
from flask import Flask, jsonify, render_template, request

from db import get_conn, init_db

app = Flask(__name__)

init_db()

import hashlib


def color_for_item(label):
    if not label:
        return "#e0e0e0"  # default gray for empty slots

    # Hash the label to get a reproducible integer
    h = int(hashlib.md5(label.encode()).hexdigest(), 16)

    # Extract RGB components from the hash
    r = (h >> 16) & 0xFF
    g = (h >> 8) & 0xFF
    b = h & 0xFF

    # Blend each channel with white (e.g. 70% original + 30% white)
    pastel_factor = 0.7
    r = int(r * pastel_factor + 255 * (1 - pastel_factor))
    g = int(g * pastel_factor + 255 * (1 - pastel_factor))
    b = int(b * pastel_factor + 255 * (1 - pastel_factor))

    return f"#{r:02x}{g:02x}{b:02x}"


def pad_slots(slots, cols=20, rows=4):
    total = cols * rows
    padded = slots[:]
    while len(padded) < total:
        # compute 1-based row/col for this new slot so numbering is consistent
        r = (len(padded) // cols) + 1
        c = (len(padded) % cols) + 1
        padded.append(
            {
                "slot_id": None,
                "item_id": None,
                "label": "",
                "color": "#e0e0e0",
                "row": r,
                "col": c,
                # location number should reflect position in grid (1..total)
                "location_numbers": [str((r - 1) * cols + c)],
                "tags": [],
                "other_names": [],
            }
        )
    return padded


def get_rack(rack_id=1):
    conn = get_conn()
    rack = conn.execute("SELECT * FROM racks WHERE id=?", (rack_id,)).fetchone()
    slots = conn.execute(
        """
        SELECT rs.id AS slot_id,
            rs.row,
            rs.col,
            i.id AS item_id,
            i.label,
            i.tags,
            i.other_names,
            i.color AS item_color
        FROM rack_slots rs
        LEFT JOIN item_slots islots 
            ON islots.slot_id = rs.id AND islots.rack_id = rs.rack_id
        LEFT JOIN items i ON i.id = islots.item_id
        WHERE rs.rack_id=?
        ORDER BY rs.row, rs.col
    """,
        (rack_id,),
    ).fetchall()
    conn.close()

    slots = [dict(s) for s in slots]

    # Database stores rack_slots.row/col as 0-based; convert to 1-based
    # so the grouping and display code (which expects rows 1..N) aligns.
    for s in slots:
        if s.get("row") is not None:
            try:
                s["row"] = int(s["row"]) + 1
            except Exception:
                pass
        if s.get("col") is not None:
            try:
                s["col"] = int(s["col"]) + 1
            except Exception:
                pass

        # convert tags/other_names (stored as comma-separated text) to lists for template usage
        tags_val = s.get("tags")
        if tags_val:
            try:
                s["tags"] = [t.strip() for t in str(tags_val).split(",") if t.strip()]
            except Exception:
                s["tags"] = []
        else:
            s["tags"] = []

        other_val = s.get("other_names")
        if other_val:
            try:
                s["other_names"] = [
                    t.strip() for t in str(other_val).split(",") if t.strip()
                ]
            except Exception:
                s["other_names"] = []
        else:
            s["other_names"] = []

        # Build mapping: item_id -> list of slot_ids
    item_locations = {}
    for s in slots:
        if s["item_id"]:
            item_locations.setdefault(s["item_id"], []).append(str(s["slot_id"]))

    # Attach location_numbers and color
    for s in slots:
        if s["item_id"]:
            s["location_numbers"] = item_locations[s["item_id"]]
        else:
            s["location_numbers"] = [str(s["slot_id"])]
        # Prefer stored item color if present, otherwise fall back to generated pastel
        if s.get("item_color"):
            s["color"] = s.get("item_color")
        else:
            s["color"] = color_for_item(s["label"])

    # Pad to full grid
    slots = pad_slots(slots, cols=rack["cols"], rows=rack["rows"])
    return rack, slots


def group_slots(slots, cols=20, rows=4):
    grouped_rows = []
    slots_by_row = {}
    for s in slots:
        slots_by_row.setdefault(s["row"], []).append(s)

    for r in range(1, rows + 1):
        row = sorted(slots_by_row.get(r, []), key=lambda x: x["col"])
        while len(row) < cols:
            row.append(
                {
                    "slot_id": None,
                    "item_id": None,
                    "label": "",
                    "color": "#e0e0e0",
                    "row": r,
                    "col": len(row) + 1,
                    "tags": [],
                    "other_names": [],
                }
            )
        merged = []
        c = 0
        while c < cols:
            s = row[c]
            span = 1
            locs = [str(s["col"])]  # or use slot_id if that’s your numbering
            while (
                c + span < cols
                and row[c + span]["item_id"] == s["item_id"]
                and s["item_id"]
            ):
                locs.append(str(row[c + span]["col"]))
                span += 1
            merged.append(
                {
                    "slot": s,
                    "span": span,
                    "color": s["color"],
                    "location_numbers": locs,
                    "tags": s.get("tags", []),
                    "other_names": s.get("other_names", []),
                }
            )
            c += span
        grouped_rows.append(merged)
    return grouped_rows


@app.get("/")
def rack_view():
    rack_id = int(request.args.get("rack", 1))  # default to rack 1
    config = request.args.get("config", "4x4")  # default to 4x4

    # Parse config to determine number of columns to display
    if config == "6x4":
        cols_to_display = 6
    else:  # default to 4x4
        cols_to_display = 4

    rack, slots = get_rack(rack_id)

    # Keep all slots, don't filter - group_slots will work with all 20 columns
    rows = group_slots(slots, cols=rack["cols"], rows=rack["rows"])

    edit_mode = request.args.get("edit", "")  # 'remove', 'item', or empty
    return render_template(
        "rack.html",
        rack=rack,
        slots=slots,
        rows=rows,
        edit_mode=edit_mode,
        remove_mode=(edit_mode == "remove"),
        edit_item_mode=(edit_mode == "item"),
        cols=cols_to_display,  # only used for display limiting
        cols_full=rack["cols"],  # full 20 columns for slicing
        rows_count=rack["rows"],
        config=config,
    )


@app.post("/items")
def create_item():
    data = request.json or {}
    label = data.get("label")
    tags = data.get("tags")
    other_names = data.get("other_names")
    color = data.get("color")
    if not label:
        return jsonify({"error": "Label required"}), 400

    # Normalize tags/other_names into comma-separated strings
    def to_csv(v):
        if v is None:
            return None
        if isinstance(v, list):
            return ",".join([str(x).strip() for x in v if str(x).strip()])
        return str(v)

    tags_csv = to_csv(tags)
    other_csv = to_csv(other_names)

    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO items(label, tags, other_names, color) VALUES(?,?,?,?)",
        (label, tags_csv, other_csv, color),
    )
    item_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify(
        {
            "item_id": item_id,
            "label": label,
            "tags": tags_csv,
            "other_names": other_csv,
            "color": color,
        }
    )


@app.post("/items/<int:item_id>/update")
def update_item(item_id):
    """Update an existing item's properties and optionally add to more slots."""
    data = request.json or {}
    label = data.get("label")
    tags = data.get("tags")
    other_names = data.get("other_names")
    color = data.get("color")
    additional_slots = data.get("additional_slots", [])  # New slots to add
    rack_id = data.get("rack_id")

    if not label:
        return jsonify({"error": "Label required"}), 400

    # Normalize tags/other_names into comma-separated strings
    def to_csv(v):
        if v is None:
            return None
        if isinstance(v, list):
            return ",".join([str(x).strip() for x in v if str(x).strip()])
        return str(v)

    tags_csv = to_csv(tags)
    other_csv = to_csv(other_names)

    conn = get_conn()

    # Check if item exists
    existing = conn.execute("SELECT id FROM items WHERE id=?", (item_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Item not found"}), 404

    # Update item properties
    conn.execute(
        "UPDATE items SET label=?, tags=?, other_names=?, color=? WHERE id=?",
        (label, tags_csv, other_csv, color, item_id),
    )

    # If additional slots provided, add item to those slots
    if additional_slots and rack_id:
        for slot_id in additional_slots:
            # Check if this slot is already occupied
            existing_placement = conn.execute(
                "SELECT item_id FROM item_slots WHERE rack_id=? AND slot_id=?",
                (rack_id, slot_id),
            ).fetchone()

            if not existing_placement:
                conn.execute(
                    "INSERT INTO item_slots(item_id, rack_id, slot_id) VALUES(?,?,?)",
                    (item_id, rack_id, slot_id),
                )

    conn.commit()
    conn.close()

    return jsonify(
        {
            "item_id": item_id,
            "label": label,
            "tags": tags_csv,
            "other_names": other_csv,
            "color": color,
            "slots_added": len(additional_slots),
        }
    )


@app.post("/place")
def place_item():
    data = request.get_json()
    item_id = data.get("item_id")
    slot_ids = data.get("slot_ids", [])
    rack_id = data.get("rack_id")
    label = data.get("label")

    # Basic validation
    if not rack_id:
        return jsonify({"error": "rack_id is required"}), 400
    if not slot_ids:
        return jsonify({"error": "slot_ids is required"}), 400
    if not label and not item_id:
        return jsonify({"error": "label is required when creating new item"}), 400

    conn = get_conn()

    # Ensure rack exists
    rack = conn.execute("SELECT id FROM racks WHERE id=?", (rack_id,)).fetchone()
    if not rack:
        conn.close()
        return jsonify({"error": f"Rack {rack_id} not found"}), 400

    # If no item_id, create a new item (include tags/other_names if provided)
    tags = data.get("tags")
    other_names = data.get("other_names")
    color = data.get("color")

    def to_csv(v):
        if v is None:
            return None
        if isinstance(v, list):
            return ",".join([str(x).strip() for x in v if str(x).strip()])
        return str(v)

    tags_csv = to_csv(tags)
    other_csv = to_csv(other_names)

    if not item_id:
        cur = conn.execute(
            "INSERT INTO items(label, tags, other_names, color) VALUES(?,?,?,?)",
            (label, tags_csv, other_csv, color),
        )
        item_id = cur.lastrowid
    else:
        # Validate existing item
        row = conn.execute(
            "SELECT label, tags, other_names, color FROM items WHERE id=?", (item_id,)
        ).fetchone()
        if row:
            label = row["label"]
            # if tags/other_names not passed in request, use values from DB
            if not tags and row.get("tags"):
                tags_csv = row.get("tags")
            if not other_names and row.get("other_names"):
                other_csv = row.get("other_names")
            # preserve existing color if not provided
            if not color and row.get("color"):
                color = row.get("color")
        else:
            conn.close()
            return jsonify({"error": f"Item {item_id} not found"}), 400

    # Place item into slots
    for sid in slot_ids:
        # Validate slot belongs to this rack
        slot = conn.execute(
            "SELECT id FROM rack_slots WHERE id=? AND rack_id=?", (sid, rack_id)
        ).fetchone()
        if not slot:
            conn.close()
            return jsonify({"error": f"Slot {sid} not valid for rack {rack_id}"}), 400

        conn.execute(
            "INSERT INTO item_slots(item_id, slot_id, item_label, rack_id, item_tags, item_other_names) VALUES(?,?,?,?,?,?)",
            (item_id, sid, label, rack_id, tags_csv, other_csv),
        )

    conn.commit()
    conn.close()

    return jsonify(
        {
            "success": True,
            "item_id": item_id,
            "label": label,
            "slot_ids": slot_ids,
            "rack_id": rack_id,
        }
    )


@app.post("/remove")
def remove_item():
    item_id = request.json.get("item_id")
    slot_id = request.json.get("slot_id")
    conn = get_conn()
    if slot_id:
        conn.execute(
            "DELETE FROM item_slots WHERE item_id=? AND slot_id=?", (item_id, slot_id)
        )
    else:
        conn.execute("DELETE FROM item_slots WHERE item_id=?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


if __name__ == "__main__":
    # Bind to 0.0.0.0 for phone/Pi access on LAN
    app.run(host="0.0.0.0", port=5000, debug=True)
