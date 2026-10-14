
import os

from flask import Flask, jsonify, request, render_template

app = Flask(
    __name__,
    template_folder="."
)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/student")
def get_student():
    return jsonify({
        "student_id": "2026-00123",
        "name": "Jasmine Rose Biboso",
        "program": "BSIT",
        "year": 3,
        "section": "A"
    })


@app.route("/hello")
def say_hello():
    name = request.args.get("name", "Student").strip()

    if not name:
        name = "Student"

    return jsonify({
        "message": f"Hello, {name}!"
    })


@app.route("/about")
def about():
    return jsonify({
        "name": "Jasmine Rose Biboso",
        "program": "BSIT",
        "year": 3,
        "section": "A",
        "Interest": "Web Development"
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
