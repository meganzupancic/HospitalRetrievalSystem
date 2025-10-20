from flask import Flask, request, render_template, redirect
from raspi_system.database_manager import (
    init_db,
    load_database_from_sqlite,
    add_item,
    delete_item_by_name,
)

app = Flask(__name__)
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
