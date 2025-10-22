# app.py

from flask import jsonify, redirect, render_template, request

# from flask_socketio import SocketIO
from raspi_system.database_manager import (
    add_or_update_item,
    delete_item_by_name,
    init_db,
    load_database_from_sqlite,
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
    item = request.form["item"]
    rack = int(request.form["rack"])
    location = int(request.form["location"])
    add_or_update_item(item, rack, location)

    # Use socketio.emit instead of emit
    socketio.emit("supply_updated")

    return "Item added", 200


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


@app.route("/api/items")
def get_items():
    items = load_database_from_sqlite()
    return jsonify(
        [
            {
                "item": entry["item"],
                "rack": entry["rack"],
                "location": entry["location"],
            }
            for entry in items
        ]
    )


@app.route("/test_emit")
def test_emit():
    socketio.emit("highlight_keyword", {"keyword": "band aid"})
    return "Test event emitted"


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
