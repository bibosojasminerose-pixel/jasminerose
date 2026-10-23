
import os
import sqlite3
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__, template_folder=".")

DATABASE = Path(
    os.environ.get(
        "DATABASE_PATH",
        str(Path(__file__).resolve().parent / "students.db")
    )
)

CLASSMATE_API_URL = os.environ.get(
    "CLASSMATE_API_URL", ""
).strip()


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def validate_student(data):
    if not isinstance(data, dict):
        return None, "Please submit valid JSON data."

    student_id = str(data.get("student_id", "")).strip()
    name = str(data.get("name", "")).strip()
    program = str(data.get("program", "")).strip()
    section = str(data.get("section", "")).strip()

    try:
        year = int(data.get("year", 0))
    except (TypeError, ValueError):
        return None, "Year must be a number from 1 to 4."

    if not all([student_id, name, program, section]):
        return None, "All student fields are required."

    if year not in (1, 2, 3, 4):
        return None, "Year must be between 1 and 4."

    if (
        len(student_id) > 50
        or len(name) > 150
        or len(program) > 100
        or len(section) > 50
    ):
        return None, "One or more fields are too long."

    return {
        "student_id": student_id,
        "name": name,
        "program": program,
        "year": year,
        "section": section
    }, None


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================================
# ORIGINAL LAB 4-7 ENDPOINTS
# ==========================================

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

    return jsonify({"message": f"Hello, {name}!"})


@app.route("/about")
def about():
    return jsonify({
        "name": "Jasmine Rose Biboso",
        "program": "BSIT",
        "year": 3,
        "section": "A",
        "interest": "Web Development"
    })


# ==========================================
# READ ALL STUDENTS
# Supports /students and /api/students
# ==========================================

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


@app.route("/api/students", methods=["GET"])
def api_students():
    connection = get_db_connection()

    try:
        students = connection.execute(
            "SELECT * FROM students ORDER BY id"
        ).fetchall()

        return jsonify([dict(student) for student in students])

    finally:
        connection.close()


# ==========================================
# CREATE STUDENT
# ==========================================

@app.route("/students", methods=["POST"])
@app.route("/api/students", methods=["POST"])
def add_student():
    data, error = validate_student(
        request.get_json(silent=True)
    )

    if error:
        return jsonify({"error": error}), 400

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO students
            (student_id, name, program, year, section)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["student_id"],
                data["name"],
                data["program"],
                data["year"],
                data["section"]
            )
        )

        connection.commit()

        student = connection.execute(
            "SELECT * FROM students WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

        return jsonify({
            "message": "Student added successfully!",
            "id": cursor.lastrowid,
            "student": dict(student)
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "This student ID already exists."
        }), 409

    finally:
        connection.close()


# ==========================================
# READ ONE STUDENT
# ==========================================

@app.route("/students/<int:id>", methods=["GET"])
@app.route("/api/students/<int:id>", methods=["GET"])
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


# ==========================================
# UPDATE STUDENT
# ==========================================

@app.route("/api/students/<int:id>", methods=["PUT"])
def update_student(id):
    data, error = validate_student(
        request.get_json(silent=True)
    )

    if error:
        return jsonify({"error": error}), 400

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE students
            SET student_id = ?,
                name = ?,
                program = ?,
                year = ?,
                section = ?
            WHERE id = ?
            """,
            (
                data["student_id"],
                data["name"],
                data["program"],
                data["year"],
                data["section"],
                id
            )
        )

        if cursor.rowcount == 0:
            return jsonify({
                "error": "Student not found."
            }), 404

        connection.commit()

        student = connection.execute(
            "SELECT * FROM students WHERE id = ?",
            (id,)
        ).fetchone()

        return jsonify({
            "message": "Student updated successfully!",
            "student": dict(student)
        })

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "This student ID already exists."
        }), 409

    finally:
        connection.close()


# ==========================================
# DELETE STUDENT
# ==========================================

@app.route("/api/students/<int:id>", methods=["DELETE"])
def delete_student(id):
    connection = get_db_connection()

    try:
        cursor = connection.execute(
            "DELETE FROM students WHERE id = ?",
            (id,)
        )

        if cursor.rowcount == 0:
            return jsonify({
                "error": "Student not found."
            }), 404

        connection.commit()

        return jsonify({
            "message": "Student deleted successfully!"
        })

    finally:
        connection.close()


# ==========================================
# FILTER BY PROGRAM
# ==========================================

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


# ==========================================
# FILTER BY YEAR
# ==========================================

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


# ==========================================
# CLASSMATE API - READ ONLY
# ==========================================

@app.route("/api/classmate", methods=["GET"])
def classmate_records():
    if not CLASSMATE_API_URL:
        return jsonify({
            "error": "Classmate API URL is not configured."
        }), 503

    try:
        response = requests.get(
            CLASSMATE_API_URL,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict):
            data = data.get("students", [])

        if not isinstance(data, list):
            return jsonify({
                "error": "Classmate API returned invalid data."
            }), 502

        return jsonify(data)

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Classmate API timed out."
        }), 504

    except (requests.exceptions.RequestException, ValueError):
        return jsonify({
            "error": "Unable to retrieve classmate records."
        }), 502


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
