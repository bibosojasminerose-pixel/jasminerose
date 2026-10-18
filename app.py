
import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request

app = Flask(__name__, template_folder=".")

DATABASE = Path(__file__).resolve().parent / "students.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/")
def home():
    return render_template("index.html")


# Original student information endpoint
@app.route("/student")
def get_student():
    return jsonify({
        "student_id": "2026-00123",
        "name": "Jasmine Rose Biboso",
        "program": "BSIT",
        "year": 3,
        "section": "A"
    })


# Greeting endpoint
@app.route("/hello")
def say_hello():
    name = request.args.get("name", "Student").strip()

    if not name:
        name = "Student"

    return jsonify({"message": f"Hello, {name}!"})


# About Me endpoint
@app.route("/about")
def about():
    return jsonify({
        "name": "Jasmine Rose Biboso",
        "program": "BSIT",
        "year": 3,
        "section": "A",
        "interest": "Web Development"
    })


# GET: Retrieve all students from SQLite
@app.route("/students", methods=["GET"])
def get_all_students():
    connection = get_db_connection()

    try:
        students = connection.execute(
            "SELECT * FROM students ORDER BY id"
        ).fetchall()

        return jsonify({
            "count": len(students),
            "students": [dict(student) for student in students]
        })
    finally:
        connection.close()


# POST: Add a new student to SQLite
@app.route("/students", methods=["POST"])
def add_student():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Please submit student information as JSON."
        }), 400

    student_id = str(data.get("student_id", "")).strip()
    name = str(data.get("name", "")).strip()
    program = str(data.get("program", "")).strip()
    section = str(data.get("section", "")).strip()

    try:
        year = int(data.get("year", 0))
    except (TypeError, ValueError):
        return jsonify({
            "error": "Year must be a number from 1 to 4."
        }), 400

    if not all([student_id, name, program, section]):
        return jsonify({
            "error": "All student fields are required."
        }), 400

    if year not in (1, 2, 3, 4):
        return jsonify({
            "error": "Year must be between 1 and 4."
        }), 400

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO students
            (student_id, name, program, year, section)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, name, program, year, section)
        )

        connection.commit()

        student = connection.execute(
            "SELECT * FROM students WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

        return jsonify({
            "message": "Student added successfully!",
            "student": dict(student)
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "This student ID already exists."
        }), 409

    finally:
        connection.close()


# GET: Retrieve one student by database ID
@app.route("/students/<int:id>", methods=["GET"])
def get_student_by_id(id):
    connection = get_db_connection()

    try:
        student = connection.execute(
            "SELECT * FROM students WHERE id = ?",
            (id,)
        ).fetchone()

        if student is None:
            return jsonify({
                "error": "Student not found."
            }), 404

        return jsonify(dict(student))
    finally:
        connection.close()


# GET: Filter students by program
@app.route("/students/program/<program>", methods=["GET"])
def get_students_by_program(program):
    connection = get_db_connection()

    try:
        students = connection.execute(
            """
            SELECT * FROM students
            WHERE LOWER(program) = LOWER(?)
            ORDER BY name
            """,
            (program,)
        ).fetchall()

        return jsonify({
            "program": program,
            "count": len(students),
            "students": [dict(student) for student in students]
        })
    finally:
        connection.close()


# GET: Filter students by year level
@app.route("/students/year/<int:year>", methods=["GET"])
def get_students_by_year(year):
    if year not in (1, 2, 3, 4):
        return jsonify({
            "error": "Year must be between 1 and 4."
        }), 400

    connection = get_db_connection()

    try:
        students = connection.execute(
            """
            SELECT * FROM students
            WHERE year = ?
            ORDER BY name
            """,
            (year,)
        ).fetchall()

        return jsonify({
            "year": year,
            "count": len(students),
            "students": [dict(student) for student in students]
        })
    finally:
        connection.close()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
