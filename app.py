from flask import Flask, request, render_template, redirect
from raspi_system.database_manager import init_db, load_database_from_sqlite, add_item

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
