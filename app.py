# app.py
import hashlib
import json
import os
import urllib.error
import urllib.request

from flask import Flask, jsonify, redirect, render_template, request

from db import get_conn, init_db

app = Flask(__name__)

init_db()

DEFAULT_PRESET_TAGS = ["Code Blue", "IV", "Sterile", "Emergency", "Disposable"]


# ---------------------------------------------------------------------------
# Auth compatibility routes (login removed)
# ---------------------------------------------------------------------------


@app.get("/login")
def login():
    """Redirect old login route to home."""
    return redirect("/")


@app.post("/login")
def login_post():
    """Redirect old login form posts to home."""
    return redirect("/")


@app.get("/logout")
def logout():
    """Compatibility logout route when auth is disabled."""
    log_event("login", "Logout link clicked (auth disabled)", None)
    return redirect("/")


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------
# Categories: "connection", "database", "login", "system"


def log_event(category: str, action: str, detail=None):
    """Write one row to system_logs.

    detail can be a plain string or a dict – dicts are serialised as JSON so
    the frontend can render structured before/after info.
    """
    try:
        if isinstance(detail, dict):
            detail_str = json.dumps(detail)
        else:
            detail_str = detail
        conn = get_conn()
        conn.execute(
            "INSERT INTO system_logs(category, action, detail) VALUES(?,?,?)",
            (category, action, detail_str),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


log_event("system", "Server started", {"message": "Flask app initialised"})


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


def normalize_preset_tags(raw_tags):
    """Normalize preset tags into a deduped ordered list of non-empty strings."""
    normalized = []
    seen = set()
    for tag in raw_tags or []:
        t = str(tag).strip()
        if not t:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(t)
    return normalized


def get_preset_tags():
    """Read preset tags from app_settings, with sane defaults."""
    conn = get_conn()
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key=?",
        ("preset_tags",),
    ).fetchone()
    conn.close()

    if not row or not row["value"]:
        return DEFAULT_PRESET_TAGS[:]

    try:
        parsed = json.loads(row["value"])
        if not isinstance(parsed, list):
            return DEFAULT_PRESET_TAGS[:]
        normalized = normalize_preset_tags(parsed)
        return normalized if normalized else DEFAULT_PRESET_TAGS[:]
    except Exception:
        return DEFAULT_PRESET_TAGS[:]


def set_preset_tags(tags):
    """Persist preset tags in app_settings."""
    normalized = normalize_preset_tags(tags)
    conn = get_conn()
    conn.execute(
        "INSERT INTO app_settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        ("preset_tags", json.dumps(normalized)),
    )
    conn.commit()
    conn.close()
    return normalized


def parse_tags_text(raw_text):
    """Parse tags from comma/newline/semicolon separated text."""
    text = str(raw_text or "")
    parts = []
    for chunk in text.replace("\n", ",").replace(";", ",").split(","):
        parts.append(chunk)
    return normalize_preset_tags(parts)


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
            slot_ids = [str(s["slot_id"]) if s.get("slot_id") else ""]
            while (
                c + span < cols
                and row[c + span]["item_id"] == s["item_id"]
                and s["item_id"]
            ):
                locs.append(str(row[c + span]["col"]))
                slot_ids.append(
                    str(row[c + span]["slot_id"])
                    if row[c + span].get("slot_id")
                    else ""
                )
                span += 1
            merged.append(
                {
                    "slot": s,
                    "span": span,
                    "slot_ids": slot_ids,
                    "col_start": s["col"],
                    "col_end": s["col"] + span - 1,
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
def home():
    """Homepage with welcome message"""
    return render_template("home.html")


@app.get("/rack/<int:rack_id>")
def rack_view(rack_id=1):
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
        preset_tags=get_preset_tags(),
    )


@app.route("/settings", methods=["GET", "POST"])
def settings_view():
    saved = False
    if request.method == "POST":
        tags = parse_tags_text(request.form.get("preset_tags", ""))
        set_preset_tags(tags)
        saved = True

    tags = get_preset_tags()
    tags_text = ", ".join(tags)
    return render_template(
        "settings.html", preset_tags=tags, tags_text=tags_text, saved=saved
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
    log_event(
        "database",
        "Item created",
        {
            "item_id": item_id,
            "name": label,
            "tags": tags_csv or "",
            "other_names": other_csv or "",
            "color": color or "",
        },
    )
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
    slot_ids = data.get("slot_ids")  # Exact slot set for this item on this rack
    rack_id = data.get("rack_id")
    resize_row = data.get("resize_row")
    resize_col_start = data.get("resize_col_start")
    resize_col_end = data.get("resize_col_end")

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

    # Check if item exists and capture before-state for the log
    existing = conn.execute(
        "SELECT label, tags, other_names, color FROM items WHERE id=?", (item_id,)
    ).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Item not found"}), 404

    before_state = {
        "name": existing["label"] or "",
        "tags": existing["tags"] or "",
        "other_names": existing["other_names"] or "",
        "color": existing["color"] or "",
    }

    # Update item properties
    conn.execute(
        "UPDATE items SET label=?, tags=?, other_names=?, color=? WHERE id=?",
        (label, tags_csv, other_csv, color, item_id),
    )

    # Prefer resize-by-range flow: compute target slot IDs server-side from row/col.
    if (
        rack_id
        and resize_row is not None
        and resize_col_start is not None
        and resize_col_end is not None
    ):
        try:
            rack_id_int = int(rack_id)
            row_ui = int(resize_row)
            col_start_ui = int(resize_col_start)
            col_end_ui = int(resize_col_end)
        except (TypeError, ValueError):
            conn.close()
            return jsonify({"error": "Invalid resize row/column values"}), 400

        if row_ui < 1 or col_start_ui < 1 or col_end_ui < col_start_ui:
            conn.close()
            return jsonify({"error": "Resize range is out of bounds"}), 400

        # rack_slots stores row/col zero-based in DB.
        row_db = row_ui - 1
        col_start_db = col_start_ui - 1
        col_end_db = col_end_ui - 1

        target_row_slots = conn.execute(
            """
            SELECT id
            FROM rack_slots
            WHERE rack_id=? AND row=? AND col BETWEEN ? AND ?
            ORDER BY col
            """,
            (rack_id_int, row_db, col_start_db, col_end_db),
        ).fetchall()

        if not target_row_slots:
            conn.close()
            return jsonify({"error": "No slots found for requested resize range"}), 400

        target_slot_ids = [int(r["id"]) for r in target_row_slots]

        # Preserve this item's placements on other rows of this rack.
        existing_item_slots = conn.execute(
            """
            SELECT islots.slot_id, rs.row
            FROM item_slots islots
            JOIN rack_slots rs ON rs.id = islots.slot_id AND rs.rack_id = islots.rack_id
            WHERE islots.item_id=? AND islots.rack_id=?
            """,
            (item_id, rack_id_int),
        ).fetchall()

        other_row_slot_ids = [
            int(r["slot_id"]) for r in existing_item_slots if int(r["row"]) != row_db
        ]
        final_slot_ids = other_row_slot_ids + target_slot_ids

        # Allow drag-resize to replace overlapped slots from other items in this row.
        placeholders = ",".join(["?"] * len(target_slot_ids))
        conn.execute(
            f"""
            DELETE FROM item_slots
            WHERE rack_id=?
              AND slot_id IN ({placeholders})
              AND item_id != ?
            """,
            [rack_id_int, *target_slot_ids, item_id],
        )

        conn.execute(
            "DELETE FROM item_slots WHERE item_id=? AND rack_id=?",
            (item_id, rack_id_int),
        )

        for sid in final_slot_ids:
            conn.execute(
                "INSERT INTO item_slots(item_id, rack_id, slot_id) VALUES(?,?,?)",
                (item_id, rack_id_int, sid),
            )

        slot_ids = final_slot_ids

    # If explicit slot_ids provided, replace this item's slot footprint on rack_id.
    if (
        slot_ids is not None
        and rack_id
        and not (
            resize_row is not None
            and resize_col_start is not None
            and resize_col_end is not None
        )
    ):
        try:
            normalized_slot_ids = [int(s) for s in slot_ids]
        except (TypeError, ValueError):
            conn.close()
            return jsonify({"error": "slot_ids must be a list of integers"}), 400

        if not normalized_slot_ids:
            conn.close()
            return jsonify({"error": "slot_ids cannot be empty"}), 400

        # Ensure all requested slots belong to this rack.
        rack_slot_rows = conn.execute(
            "SELECT id FROM rack_slots WHERE rack_id=?",
            (rack_id,),
        ).fetchall()
        valid_slot_ids = {int(r["id"]) for r in rack_slot_rows}
        if any(sid not in valid_slot_ids for sid in normalized_slot_ids):
            conn.close()
            return (
                jsonify({"error": "One or more slot_ids are invalid for this rack"}),
                400,
            )

        # Ensure requested slots are either empty or already owned by this item.
        placeholders = ",".join(["?"] * len(normalized_slot_ids))
        occupied_by_other = conn.execute(
            f"""
            SELECT slot_id
            FROM item_slots
            WHERE rack_id=?
              AND slot_id IN ({placeholders})
              AND item_id != ?
            """,
            [rack_id, *normalized_slot_ids, item_id],
        ).fetchall()
        if occupied_by_other:
            conn.close()
            return (
                jsonify(
                    {"error": "Cannot resize into a slot already used by another item"}
                ),
                409,
            )

        conn.execute(
            "DELETE FROM item_slots WHERE item_id=? AND rack_id=?",
            (item_id, rack_id),
        )

        for sid in normalized_slot_ids:
            conn.execute(
                "INSERT INTO item_slots(item_id, rack_id, slot_id) VALUES(?,?,?)",
                (item_id, rack_id, sid),
            )

        slot_ids = normalized_slot_ids

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
    after_state = {
        "name": label,
        "tags": tags_csv or "",
        "other_names": other_csv or "",
        "color": color or "",
    }
    log_event(
        "database",
        "Item updated",
        {
            "item_id": item_id,
            "before": before_state,
            "after": after_state,
            "slots_added": additional_slots,
            "slots_set": slot_ids,
            "rack_id": rack_id,
        },
    )
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

    # Resolve rack name for the log
    log_conn = get_conn()
    rack_row = log_conn.execute(
        "SELECT name FROM racks WHERE id=?", (rack_id,)
    ).fetchone()
    log_conn.close()
    rack_name = rack_row["name"] if rack_row else f"Rack {rack_id}"

    conn.commit()
    conn.close()
    log_event(
        "database",
        "Item placed",
        {
            "item_id": item_id,
            "name": label,
            "rack_id": rack_id,
            "rack_name": rack_name,
            "slot_ids": slot_ids,
            "tags": tags_csv or "",
            "other_names": other_csv or "",
        },
    )
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
    # Fetch label for log before deleting
    row = conn.execute(
        "SELECT i.label, GROUP_CONCAT(DISTINCT r.name) AS rack_names, GROUP_CONCAT(DISTINCT islots.slot_id) AS slot_ids"
        " FROM items i"
        " LEFT JOIN item_slots islots ON islots.item_id = i.id"
        " LEFT JOIN racks r ON r.id = islots.rack_id"
        " WHERE i.id=?",
        (item_id,),
    ).fetchone()
    item_label = row["label"] if row else str(item_id)
    rack_names = row["rack_names"] if row else ""
    all_slot_ids = row["slot_ids"] if row else ""
    if slot_id:
        conn.execute(
            "DELETE FROM item_slots WHERE item_id=? AND slot_id=?", (item_id, slot_id)
        )
        log_detail = {
            "item_id": item_id,
            "name": item_label,
            "scope": "single slot",
            "slot_id": slot_id,
            "racks": rack_names,
        }
    else:
        conn.execute("DELETE FROM item_slots WHERE item_id=?", (item_id,))
        log_detail = {
            "item_id": item_id,
            "name": item_label,
            "scope": "all slots",
            "slot_ids": all_slot_ids,
            "racks": rack_names,
        }
    conn.commit()
    conn.close()
    log_event("database", "Item removed", log_detail)
    return jsonify({"ok": True})


@app.route("/edit-racks")
def edit_racks():
    """Page for editing rack configurations"""
    conn = get_conn()
    racks = conn.execute("SELECT * FROM racks ORDER BY id").fetchall()
    conn.close()
    rack_list = [dict(r) for r in racks]
    # Add default config if not set
    for rack in rack_list:
        if not rack.get("config"):
            rack["config"] = "4x4"
    return render_template("edit_racks.html", racks=rack_list)


# In-memory rack connection status store.
# Possible states: "connected", "disconnected", "reconnecting"
_rack_status = {
    1: "disconnected",
    2: "disconnected",
    3: "disconnected",
    4: "disconnected",
}


@app.route("/connection-status")
def connection_status():
    """Page showing Arduino/BLE connection status"""
    conn = get_conn()
    racks = conn.execute("SELECT id, name FROM racks ORDER BY id LIMIT 4").fetchall()
    conn.close()
    rack_list = [dict(r) for r in racks]
    # Pad to 4 racks in case DB has fewer
    existing_ids = {r["id"] for r in rack_list}
    for i in range(1, 5):
        if i not in existing_ids:
            rack_list.append({"id": i, "name": f"Rack {i}"})
    rack_list.sort(key=lambda r: r["id"])
    return render_template("connection_status.html", racks=rack_list)


@app.get("/api/rack-status")
def get_rack_status():
    """Return BLE connection status for all 4 racks."""
    return jsonify({str(k): v for k, v in _rack_status.items()})


@app.post("/api/rack-status")
def update_rack_status():
    """Allow the raspi system to push rack connection state updates."""
    data = request.get_json(force=True)
    rack_id = data.get("rack_id")
    status = data.get("status")

    # Be permissive with incoming payloads from edge devices.
    # Accept rack_id as int-like strings and status in mixed case.
    try:
        rack_id = int(rack_id)
    except (TypeError, ValueError):
        rack_id = None

    if isinstance(status, str):
        status = status.strip().lower()

    if rack_id not in (1, 2, 3, 4) or status not in (
        "connected",
        "disconnected",
        "reconnecting",
    ):
        return jsonify({"error": "Invalid rack_id or status"}), 400
    _rack_status[rack_id] = status
    action_label = {
        "connected": "Rack connected",
        "disconnected": "Rack disconnected",
        "reconnecting": "Rack reconnecting",
    }.get(status, status)
    # Resolve rack name
    _rc = get_conn()
    _rr = _rc.execute("SELECT name FROM racks WHERE id=?", (rack_id,)).fetchone()
    _rc.close()
    rack_name = _rr["name"] if _rr else f"Rack {rack_id}"
    log_event(
        "connection",
        action_label,
        {
            "rack_id": rack_id,
            "rack_name": rack_name,
            "status": status,
        },
    )
    return jsonify({"ok": True})


@app.post("/api/ui-debug")
def ui_debug_event():
    """Receive lightweight client-side debug telemetry for UI troubleshooting."""
    data = request.get_json(silent=True) or {}
    event = str(data.get("event") or "unknown")
    detail = {
        "event": event,
        "rack_id": data.get("rack_id"),
        "item_id": data.get("item_id"),
        "row": data.get("row"),
        "left": data.get("left"),
        "right": data.get("right"),
        "reason": data.get("reason"),
    }
    app.logger.info("UI_DEBUG %s", json.dumps(detail, default=str))
    return jsonify({"ok": True})


@app.post("/api/live-highlight")
def live_highlight_slots():
    """Forward live rack slot highlights to the Pi BLE control API."""
    data = request.get_json(silent=True) or {}

    try:
        rack_id = int(data.get("rack_id"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid rack_id"}), 400

    if rack_id not in (1, 2, 3, 4):
        return jsonify({"ok": False, "error": "Invalid rack_id"}), 400

    clear_requested = bool(data.get("clear", False))
    if clear_requested:
        base_url = os.environ.get("HRS_BLE_CONTROL_BASE", "http://127.0.0.1:8765")
        url = f"{base_url.rstrip('/')}/highlight-slots"
        payload = json.dumps(
            {
                "rack_id": rack_id,
                "clear": True,
                "source": str(data.get("source") or "ui"),
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                body = resp.read().decode("utf-8") or "{}"
                result = json.loads(body)
                return jsonify(result), (200 if result.get("ok") else 500)
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8") or "{}"
                err_data = json.loads(body)
                message = err_data.get("message") or err_data.get("error")
            except Exception:
                message = None
            return (
                jsonify(
                    {
                        "ok": False,
                        "rack_id": rack_id,
                        "error": message
                        or "BLE control service rejected live highlight clear",
                    }
                ),
                500,
            )
        except Exception as e:
            return (
                jsonify(
                    {
                        "ok": False,
                        "rack_id": rack_id,
                        "error": f"Could not reach BLE control service: {e}",
                    }
                ),
                500,
            )

    raw_slot_ids = data.get("slot_ids") or []
    if not isinstance(raw_slot_ids, list):
        return jsonify({"ok": False, "error": "slot_ids must be a list"}), 400

    parsed_slot_ids = []
    for sid in raw_slot_ids:
        try:
            parsed_slot_ids.append(int(sid))
        except (TypeError, ValueError):
            continue

    # Convert DB rack_slots IDs to rack-local slot indexes expected by BLE (1..80).
    # rack_slots.row/col are stored zero-based in DB.
    normalized_slot_ids = []
    if parsed_slot_ids:
        conn = get_conn()
        rack_row = conn.execute(
            "SELECT cols FROM racks WHERE id=?",
            (rack_id,),
        ).fetchone()
        rack_cols = int(rack_row["cols"]) if rack_row and rack_row["cols"] else 20

        placeholders = ",".join(["?"] * len(parsed_slot_ids))
        slot_rows = conn.execute(
            f"""
            SELECT id, row, col
            FROM rack_slots
            WHERE rack_id=? AND id IN ({placeholders})
            """,
            [rack_id, *parsed_slot_ids],
        ).fetchall()
        conn.close()

        id_to_local = {}
        for r in slot_rows:
            try:
                row_db = int(r["row"])
                col_db = int(r["col"])
                local_slot = (row_db * rack_cols) + col_db + 1
            except (TypeError, ValueError):
                continue
            if 1 <= local_slot <= 80:
                id_to_local[int(r["id"])] = local_slot

        for sid in parsed_slot_ids:
            # Prefer DB mapping; fallback allows already-local slot payloads.
            local = id_to_local.get(sid)
            if local is None and 1 <= sid <= 80:
                local = sid
            if local is not None:
                normalized_slot_ids.append(local)

    # Preserve order while removing duplicates.
    normalized_slot_ids = list(dict.fromkeys(normalized_slot_ids))

    if not normalized_slot_ids:
        return jsonify({"ok": False, "error": "No valid slot_ids"}), 400

    app.logger.info(
        "LIVE_HIGHLIGHT rack=%s input=%s translated=%s",
        rack_id,
        raw_slot_ids,
        normalized_slot_ids,
    )

    base_url = os.environ.get("HRS_BLE_CONTROL_BASE", "http://127.0.0.1:8765")
    url = f"{base_url.rstrip('/')}/highlight-slots"
    payload = json.dumps(
        {
            "rack_id": rack_id,
            "slot_ids": normalized_slot_ids,
            "source": str(data.get("source") or "ui"),
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read().decode("utf-8") or "{}"
            result = json.loads(body)
            return jsonify(result), (200 if result.get("ok") else 500)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8") or "{}"
            err_data = json.loads(body)
            message = err_data.get("message") or err_data.get("error")
        except Exception:
            message = None
        return (
            jsonify(
                {
                    "ok": False,
                    "rack_id": rack_id,
                    "error": message or "BLE control service rejected live highlight",
                }
            ),
            500,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "ok": False,
                    "rack_id": rack_id,
                    "error": f"Could not reach BLE control service: {e}",
                }
            ),
            500,
        )


@app.post("/api/manual-connect/<int:rack_id>")
def manual_connect_rack(rack_id):
    """Manually trigger BLE connect attempt for a rack via Pi control API."""
    if rack_id not in (1, 2, 3, 4):
        return jsonify({"ok": False, "error": "Invalid rack_id"}), 400

    _rack_status[rack_id] = "reconnecting"
    base_url = os.environ.get("HRS_BLE_CONTROL_BASE", "http://127.0.0.1:8765")
    url = f"{base_url.rstrip('/')}/manual-connect"
    payload = json.dumps({"rack_id": rack_id}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read().decode("utf-8") or "{}"
            data = json.loads(body)
            ok = bool(data.get("ok"))
            _rack_status[rack_id] = "connected" if ok else "disconnected"
            return jsonify(data), (200 if ok else 500)
    except urllib.error.HTTPError as e:
        _rack_status[rack_id] = "disconnected"
        try:
            body = e.read().decode("utf-8") or "{}"
            data = json.loads(body)
            message = data.get("message") or data.get("error")
        except Exception:
            message = None
        return (
            jsonify(
                {
                    "ok": False,
                    "rack_id": rack_id,
                    "error": message or f"Manual connect failed for rack {rack_id}",
                }
            ),
            500,
        )
    except Exception as e:
        _rack_status[rack_id] = "disconnected"
        return (
            jsonify(
                {
                    "ok": False,
                    "rack_id": rack_id,
                    "error": f"Could not reach BLE control service: {e}",
                }
            ),
            500,
        )


@app.post("/rack/<int:rack_id>/config")
def update_rack_config(rack_id):
    """Update rack configuration (4x4 or 6x4)"""
    data = request.get_json()
    config = data.get("config")

    if config not in ["4x4", "6x4"]:
        return jsonify({"error": "Invalid config. Must be '4x4' or '6x4'"}), 400

    conn = get_conn()
    rack = conn.execute(
        "SELECT id, name, config FROM racks WHERE id=?", (rack_id,)
    ).fetchone()
    if not rack:
        conn.close()
        return jsonify({"error": f"Rack {rack_id} not found"}), 404

    old_config = rack["config"] or "4x4"
    rack_name = rack["name"]
    conn.execute("UPDATE racks SET config = ? WHERE id = ?", (config, rack_id))
    conn.commit()
    conn.close()
    log_event(
        "database",
        "Rack config updated",
        {
            "rack_id": rack_id,
            "rack_name": rack_name,
            "before": old_config,
            "after": config,
        },
    )
    return jsonify({"success": True, "config": config})


@app.route("/logs")
def view_logs():
    """Page for viewing system logs"""
    log_event("login", "Logs page viewed", None)
    return render_template("logs.html")


@app.get("/api/logs")
def api_logs():
    """Return log entries filtered by category and time window."""
    category = request.args.get(
        "category", "all"
    )  # all|connection|database|login|system
    hours = request.args.get("hours", "24")  # 1|6|24|168|0 (0=all time)
    limit = int(request.args.get("limit", "500"))

    conn = get_conn()
    params = []
    where_clauses = []

    try:
        hours_int = int(hours)
    except ValueError:
        hours_int = 24

    if hours_int > 0:
        where_clauses.append("timestamp >= datetime('now', ? || ' hours')")
        params.append(f"-{hours_int}")

    if category != "all":
        where_clauses.append("category = ?")
        params.append(category)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params.append(limit)

    rows = conn.execute(
        f"SELECT id, timestamp, category, action, detail FROM system_logs {where_sql} ORDER BY id DESC LIMIT ?",
        params,
    ).fetchall()
    conn.close()

    out = []
    for r in rows:
        entry = dict(r)
        if entry.get("detail"):
            try:
                entry["detail"] = json.loads(entry["detail"])
            except (json.JSONDecodeError, TypeError):
                pass  # leave as plain string
        out.append(entry)
    return jsonify(out)


if __name__ == "__main__":
    # Bind to 0.0.0.0 for phone/Pi access on LAN
    app.run(host="0.0.0.0", port=5000, debug=True)
