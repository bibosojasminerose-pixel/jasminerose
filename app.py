
import os
import sqlite3
import logging
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, render_template, request

# =========================================================
# STUDENTHUB | LABORATORY ACTIVITY 9
# Flask REST API + SQLite + Partner API Integration
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder="templates" if (BASE_DIR / "templates").is_dir() else "."
)

logging.basicConfig(level=logging.INFO)

DATABASE = Path(
    os.environ.get("DATABASE_PATH", str(BASE_DIR / "students.db"))
)

# Configure this in Render using your assigned partner's URL.
CLASSMATE_API_URL = os.environ.get(
    "CLASSMATE_API_URL",
    "https://johnmarkalarba.onrender.com/api/students"
).strip().rstrip("/")

HTTP = requests.Session()


# =========================================================
# DATABASE
# =========================================================

def get_db_connection():
    conn = sqlite3.connect(str(DATABASE), timeout=20)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_database():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)

    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                program TEXT NOT NULL,
                year INTEGER NOT NULL,
                section TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'Local'
            )
        """)

        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(students)")
        }

        if "source" not in columns:
            conn.execute("""
                ALTER TABLE students
                ADD COLUMN source TEXT NOT NULL DEFAULT 'Local'
            """)

        conn.execute("""
            UPDATE students
            SET source = 'Local'
            WHERE source IS NULL OR TRIM(source) = ''
        """)


# =========================================================
# VALIDATION
# =========================================================

def validate_student(payload):
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object."

    fields = ("student_id", "name", "program", "section")
    data = {
        key: str(payload.get(key, "")).strip()
        for key in fields
    }

    if any(not data[key] for key in fields):
        return None, (
            "Student ID, name, program, and section are required."
        )

    limits = {
        "student_id": 50,
        "name": 150,
        "program": 100,
        "section": 50,
    }

    for key, maximum in limits.items():
        if len(data[key]) > maximum:
            return None, f"{key} must not exceed {maximum} characters."

    try:
        year = int(payload.get("year"))
    except (TypeError, ValueError, OverflowError):
        return None, "Year must be between 1 and 4."

    if year not in (1, 2, 3, 4):
        return None, "Year must be between 1 and 4."

    data["year"] = year
    return data, None


def save_student(data, source="Local"):
    with get_db_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO students
                (student_id, name, program, year, section, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["student_id"],
            data["name"],
            data["program"],
            data["year"],
            data["section"],
            source,
        ))

        row = conn.execute(
            "SELECT * FROM students WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

        return dict(row)


# =========================================================
# PARTNER API CONFIGURATION
# =========================================================

def partner_config_error():
    parsed = urlparse(CLASSMATE_API_URL)

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") not in ("/students", "/api/students")
    ):
        return (
            "Set CLASSMATE_API_URL to your assigned partner's HTTPS "
            "endpoint ending in /students or /api/students."
        )

    if not parsed.hostname.endswith(".onrender.com"):
        return "CLASSMATE_API_URL must point to your assigned Render service."

    return None


def extract_students(result):
    if isinstance(result, list):
        return result

    if not isinstance(result, dict):
        return None

    for key in ("students", "data", "records"):
        value = result.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            nested = extract_students(value)
            if nested is not None:
                return nested

    if "student_id" in result and (
        "name" in result or "full_name" in result
    ):
        return [result]

    return None


def normalize_partner_student(student):
    """Normalize common field names returned by partner APIs."""
    if not isinstance(student, dict):
        return None

    name = student.get("name") or student.get("full_name")

    normalized = {
        "student_id": student.get("student_id"),
        "name": name,
        "program": student.get("program"),
        "year": student.get("year", student.get("year_level")),
        "section": student.get("section"),
    }

    data, error = validate_student(normalized)
    return data if not error else None


def partner_request(method, payload=None):
    config_error = partner_config_error()

    if config_error:
        return None, config_error, 503

    try:
        response = HTTP.request(
            method,
            CLASSMATE_API_URL,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=(10, 35),
            allow_redirects=True,
        )

    except requests.Timeout:
        return None, (
            "The partner API timed out. Check whether the partner's "
            "Render service is awake and responding."
        ), 504

    except requests.RequestException as exc:
        app.logger.exception("Partner connection failed")
        return None, f"Could not connect to partner API: {exc}", 502

    # A redirect to an HTML page may indicate a wrong endpoint.
    content_type = response.headers.get("Content-Type", "")

    try:
        result = response.json()
    except ValueError:
        result = None

    if not response.ok:
        if isinstance(result, dict):
            detail = (
                result.get("details")
                or result.get("error")
                or result.get("message")
            )
        else:
            detail = None

        detail = detail or response.text[:500] or "No response details"

        return None, (
            f"Partner API returned HTTP {response.status_code}: {detail}"
        ), 502

    if result is None:
        detail = (
            response.text[:300]
            if response.text
            else "The response body is empty."
        )

        return None, (
            f"Partner API returned a non-JSON response "
            f"({content_type or 'unknown content type'}). "
            f"Check the endpoint. Response: {detail}"
        ), 502

    # A partner may return HTTP 200 with an application-level error.
    if isinstance(result, dict) and result.get("success") is False:
        detail = (
            result.get("details")
            or result.get("error")
            or result.get("message")
            or "Partner rejected the request."
        )
        return None, f"Partner rejected the request: {detail}", 502

    return result, None, response.status_code


# =========================================================
# HOME AND PREVIOUS LAB ENDPOINTS
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/student")
def get_student():
    return jsonify({
        "student_id": "2026-00123",
        "name": "Sample Student",
        "program": "BSIT",
        "year": 3,
        "section": "A",
    })


@app.route("/hello")
def say_hello():
    name = request.args.get("name", "Student").strip() or "Student"
    return jsonify({"message": f"Hello, {name}!"})


@app.route("/about")
def about():
    return jsonify({
        "name": "Jasmine Rose Biboso",
        "program": "BSIT",
        "year": 3,
        "section": "A",
        "interest": "Web Development",
    })


# =========================================================
# LOCAL CRUD
# =========================================================

def all_students():
    with get_db_connection() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM students ORDER BY id"
            )
        ]


@app.route("/students", methods=["GET"])
def get_all_students():
    students = all_students()
    return jsonify({"count": len(students), "students": students})


@app.route("/api/students", methods=["GET"])
def api_students():
    return jsonify(all_students())


@app.route("/students", methods=["POST"])
@app.route("/api/students", methods=["POST"])
def add_student():
    payload = request.get_json(silent=True)
    data, error = validate_student(payload)

    if error:
        return jsonify({"error": error}), 400

    # Imported records should use /import-student instead.
    source = "Local"

    try:
        student = save_student(data, source)
        return jsonify({
            "success": True,
            "message": "Student added successfully!",
            "student": student,
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "success": False,
            "error": "This student ID already exists.",
        }), 409


@app.route("/students/<int:id>", methods=["GET"])
@app.route("/api/students/<int:id>", methods=["GET"])
def get_student_by_id(id):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM students WHERE id = ?", (id,)
        ).fetchone()

    if row is None:
        return jsonify({"error": "Student not found."}), 404

    return jsonify(dict(row))


@app.route("/api/students/<int:id>", methods=["PUT"])
def update_student(id):
    data, error = validate_student(request.get_json(silent=True))

    if error:
        return jsonify({"error": error}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                UPDATE students
                SET student_id = ?, name = ?, program = ?,
                    year = ?, section = ?
                WHERE id = ?
            """, (
                data["student_id"], data["name"], data["program"],
                data["year"], data["section"], id,
            ))

            if cursor.rowcount == 0:
                return jsonify({"error": "Student not found."}), 404

            row = conn.execute(
                "SELECT * FROM students WHERE id = ?", (id,)
            ).fetchone()

        return jsonify({
            "success": True,
            "message": "Student updated successfully!",
            "student": dict(row),
        })

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "This student ID already exists."
        }), 409


@app.route("/api/students/<int:id>", methods=["DELETE"])
def delete_student(id):
    with get_db_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM students WHERE id = ?", (id,)
        )

    if cursor.rowcount == 0:
        return jsonify({"error": "Student not found."}), 404

    return jsonify({"message": "Student deleted successfully!"})


@app.route("/students/program/<program>")
def get_students_by_program(program):
    with get_db_connection() as conn:
        students = [
            dict(row)
            for row in conn.execute("""
                SELECT * FROM students
                WHERE LOWER(program) = LOWER(?)
                ORDER BY name
            """, (program,))
        ]

    return jsonify({
        "program": program,
        "count": len(students),
        "students": students,
    })


@app.route("/students/year/<int:year>")
def get_students_by_year(year):
    if year not in (1, 2, 3, 4):
        return jsonify({"error": "Year must be between 1 and 4."}), 400

    with get_db_connection() as conn:
        students = [
            dict(row)
            for row in conn.execute("""
                SELECT * FROM students
                WHERE year = ?
                ORDER BY name
            """, (year,))
        ]

    return jsonify({
        "year": year,
        "count": len(students),
        "students": students,
    })


# =========================================================
# RETRIEVE PARTNER RECORDS
# GET /partner-records
# =========================================================

@app.route("/partner-records", methods=["GET"])
@app.route("/api/classmate", methods=["GET"])
def partner_records():
    result, error, status = partner_request("GET")

    if error:
        return jsonify({
            "error": "Unable to retrieve partner records.",
            "details": error,
            "partner_status": status,
        }), status

    students = extract_students(result)

    if students is None:
        return jsonify({
            "error": "Partner response does not contain a student list.",
            "details": "Expected a JSON list or an object containing students.",
        }), 502

    return jsonify({
        "count": len(students),
        "students": students,
    })


# =========================================================
# IMPORT PARTNER RECORD
# POST /import-student
# =========================================================

@app.route("/import-student", methods=["POST"])
def import_student():
    data, error = validate_student(request.get_json(silent=True))

    if error:
        return jsonify({"error": error}), 400

    try:
        student = save_student(data, "Classmate API")
        return jsonify({
            "success": True,
            "message": "Partner record imported successfully!",
            "student": student,
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "This student ID already exists in your database."
        }), 409


# =========================================================
# SEND PRACTICE RECORD TO PARTNER
# POST /send-partner-record
# =========================================================

@app.route("/send-partner-record", methods=["POST"])
def send_partner_record():
    data, error = validate_student(request.get_json(silent=True))

    if error:
        return jsonify({
            "success": False,
            "error": error,
        }), 400

    payload = {
        "student_id": data["student_id"],
        "name": data["name"],
        "program": data["program"],
        "year": data["year"],
        "section": data["section"],
    }

    result, error, status = partner_request("POST", payload)

    if error:
        app.logger.error("Partner send failed: %s", error)
        return jsonify({
            "success": False,
            "error": "Unable to send record to partner.",
            "details": error,
            "partner_status": status,
        }), status

    return jsonify({
        "success": True,
        "message": "Student record sent to partner successfully!",
        "partner_response": result,
    }), 200


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():
    config_error = partner_config_error()

    return jsonify({
        "status": "ok",
        "service": "StudentHub",
        "database": "SQLite",
        "partner_configured": config_error is None,
        "partner_config_error": config_error,
        # Do not expose internal service configuration unnecessarily.
    })


# =========================================================
# START APPLICATION
# =========================================================

ensure_database()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
    )
