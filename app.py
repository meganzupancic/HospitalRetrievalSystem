# app.py

from flask import jsonify, redirect, render_template, request

# from flask_socketio import SocketIO
from raspi_system.database_manager import (
    add_or_update_item,
    delete_item_by_name,
    init_db,
    load_database_from_sqlite,
    update_item_by_id,
    delete_item_by_id,
    add_current_item,
    get_current_items,
    delete_current_item,
    get_distinct_items,
)
from socketio_instance import app, socketio

# app = Flask(__name__)
# socketio = SocketIO(app, cors_allowed_origins="*")
init_db()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        item = request.form["item"]
        rack = int(request.form["rack"])
        location = int(request.form["location"])
        add_or_update_item(item, rack, location)
        return redirect("/")

    items = load_database_from_sqlite()
    return render_template("index.html", items=items)


@app.route("/add_item", methods=["POST"])
def add_item_route():
    print("\n📝 /add_item received:", request.form)
    item = request.form["item"]
    rack = int(request.form["rack"])
    location = int(request.form["location"])
    print(f"➡️ Adding item '{item}' at rack {rack}, location {location}")
    
    # Add item to DB
    new_id = add_or_update_item(item, rack, location)
    
    # Verify it was added by loading DB
    items = load_database_from_sqlite()
    matching = [i for i in items if i["item"] == item and i["rack"] == rack and i["location"] == location]
    print(f"✓ Found {len(matching)} matching items in DB after add")
    
    # Emit update
    socketio.emit("supply_updated")
    print("✅ Item added and supply_updated emitted")
    return jsonify({"id": new_id, "item": item, "rack": rack, "location": location}), 201


@app.route("/delete_by_name", methods=["POST"])
def delete_by_name():
    item_name = request.form["item_name"]
    delete_item_by_name(item_name)
    return redirect("/")


@app.route("/update_location", methods=["POST"])
def update_location():
    item = request.form["item"]
    rack = int(request.form["rack"])
    location = int(request.form["location"])
    add_or_update_item(item, rack, location)

    socketio.emit("supply_updated")

    return "Updated", 200


@app.route("/move_item", methods=["POST"])
def move_item():
    # Expects form fields: id, rack, location
    row_id = int(request.form.get("id"))
    rack = int(request.form.get("rack"))
    location = int(request.form.get("location"))
    print(f"Moving DB row {row_id} to rack {rack}, location {location}")
    update_item_by_id(row_id, rack, location)
    socketio.emit("supply_updated")
    return "Moved", 200


@app.route("/delete_item", methods=["POST"])
def delete_item():
    # Expects form field: id
    row_id = int(request.form.get("id"))
    print(f"Deleting DB row {row_id}")
    delete_item_by_id(row_id)
    socketio.emit("supply_updated")
    return "Deleted", 200


@app.route("/api/items")
def get_items():
    items = load_database_from_sqlite()
    return jsonify(items)


@app.route("/api/distinct_items")
def get_distinct_items_route():
    items = get_distinct_items()
    return jsonify(items)

@app.route('/api/delete_item_by_name', methods=['POST'])
def api_delete_item_by_name():
    # Accept form-encoded or JSON
    item = request.form.get('item') or (request.get_json() or {}).get('item')
    if not item:
        return jsonify({'error': 'item required'}), 400
    print(f"Deleting all occurrences of item: {item}")
    try:
        delete_item_by_name(item)
        # Also remove from current_items table if present
        try:
            delete_current_item(item)
        except Exception:
            pass
        socketio.emit('supply_updated')
        return jsonify({'status': 'deleted', 'item': item}), 200
    except Exception as e:
        print('Error deleting item by name:', e)
        return jsonify({'error': str(e)}), 500

@app.route("/api/current_items")
def get_current_items_route():
    items = get_current_items()
    return jsonify(items)

@app.route("/api/current_items", methods=["POST"])
def add_current_item_route():
    item = request.form.get("item")
    if not item:
        return "Item name required", 400
    add_current_item(item)
    return "Added", 200

@app.route("/api/current_items", methods=["DELETE"])
def delete_current_item_route():
    item = request.args.get("item")
    if not item:
        return "Item name required", 400
    delete_current_item(item)
    return "Deleted", 200


@app.route("/test_emit")
def test_emit():
    socketio.emit("highlight_keyword", {"keyword": "band aid"})
    return "Test event emitted"


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
