# app.py

from flask import Flask, redirect, render_template, request
from flask_socketio import SocketIO

from raspi_system.database_manager import (
    add_item,
    delete_item_by_name,
    init_db,
    load_database_from_sqlite,
)

app = Flask(__name__)
socketio = SocketIO(app)
init_db()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        item = request.form["item"]
        rack = int(request.form["rack"])
        location = int(request.form["location"])
        add_item(item, rack, location)
        return redirect("/")

    items = load_database_from_sqlite()
    return render_template("index.html", items=items)


@app.route("/delete_by_name", methods=["POST"])
def delete_by_name():
    item_name = request.form["item_name"]
    delete_item_by_name(item_name)
    return redirect("/")


@app.route("/test_emit")
def test_emit():
    socketio.emit("highlight_keyword", {"keyword": "band aid"})
    return "Test event emitted"


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
