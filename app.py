import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder='templates' if (BASE_DIR / 'templates').is_dir() else '.')
DATABASE = Path(os.environ.get('DATABASE_PATH', str(BASE_DIR / 'students.db')))
CLASSMATE_API_URL = os.environ.get('CLASSMATE_API_URL', '').strip().rstrip('/')


def get_db_connection():
    connection = sqlite3.connect(DATABASE, timeout=15)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_database():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            program TEXT NOT NULL,
            year INTEGER NOT NULL,
            section TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'Local'
        )''')
        cols = {r['name'] for r in conn.execute('PRAGMA table_info(students)')}
        if 'source' not in cols:
            conn.execute("ALTER TABLE students ADD COLUMN source TEXT NOT NULL DEFAULT 'Local'")
        conn.execute("UPDATE students SET source='Local' WHERE source IS NULL OR TRIM(source) = ''")


def validate_student(payload):
    if not isinstance(payload, dict):
        return None, 'Submit a JSON object.'
    values = {k: str(payload.get(k, '')).strip() for k in ('student_id', 'name', 'program', 'section')}
    if any(not v for v in values.values()):
        return None, 'Student ID, name, program, and section are required.'
    if any(len(values[k]) > maximum for k, maximum in {'student_id': 50, 'name': 150, 'program': 100, 'section': 50}.items()):
        return None, 'One or more fields are too long.'
    try:
        year = int(payload.get('year'))
    except (ValueError, TypeError):
        return None, 'Year must be between 1 and 4.'
    if year not in (1, 2, 3, 4):
        return None, 'Year must be between 1 and 4.'
    values['year'] = year
    return values, None


def save_student(data, source):
    with get_db_connection() as conn:
        cursor = conn.execute('''INSERT INTO students (student_id, name, program, year, section, source)
                                 VALUES (?, ?, ?, ?, ?, ?)''',
                              (data['student_id'], data['name'], data['program'], data['year'], data['section'], source))
        row = conn.execute('SELECT * FROM students WHERE id=?', (cursor.lastrowid,)).fetchone()
        return dict(row)


def partner_config_error():
    parsed = urlparse(CLASSMATE_API_URL)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path.rstrip('/') != '/api/students':
        return 'Set CLASSMATE_API_URL to your assigned partner HTTPS /api/students endpoint.'
    # Restrict outgoing requests to the configured Render service.
    if not parsed.hostname.endswith('.onrender.com'):
        return 'Partner URL must be an assigned Render HTTPS service.'
    return None


def partner_request(method, payload=None):
    error = partner_config_error()
    if error:
        return None, error, 503
    try:
        response = requests.request(method, CLASSMATE_API_URL, json=payload, timeout=15, allow_redirects=False)
        if 300 <= response.status_code < 400:
            return None, 'Partner API redirected unexpectedly.', 502
        if not response.ok:
            return None, f'Partner API returned HTTP {response.status_code}.', 502
        try:
            return response.json(), None, response.status_code
        except ValueError:
            return None, 'Partner API did not return JSON.', 502
    except requests.Timeout:
        return None, 'Partner API timed out.', 504
    except requests.RequestException:
        return None, 'Unable to contact partner API.', 502


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/student')
def get_student():
    return jsonify({'student_id': '2026-00123', 'name': 'Sample Student', 'program': 'BSIT', 'year': 3, 'section': 'A'})


@app.route('/hello')
def say_hello():
    return jsonify({'message': f"Hello, {request.args.get('name', 'Student').strip() or 'Student'}!"})


@app.route('/about')
def about():
    return jsonify({'name': 'Jasmine Rose Biboso', 'program': 'BSIT', 'year': 3, 'section': 'A', 'interest': 'Web Development'})


@app.route('/students', methods=['GET'])
def get_all_students():
    with get_db_connection() as conn:
        students = [dict(r) for r in conn.execute('SELECT * FROM students ORDER BY id')]
    return jsonify({'count': len(students), 'students': students})


@app.route('/api/students', methods=['GET'])
def api_students():
    with get_db_connection() as conn:
        students = [dict(r) for r in conn.execute('SELECT * FROM students ORDER BY id')]
    return jsonify(students)


@app.route('/students', methods=['POST'])
@app.route('/api/students', methods=['POST'])
def add_student():
    raw = request.get_json(silent=True)
    data, error = validate_student(raw)
    if error:
        return jsonify({'error': error}), 400
    # Source is determined by the receiving application; partner requests use Partner API.
    source = 'External API'
    if request.path == '/students' or (isinstance(raw, dict) and raw.get('source') == 'Local'):
        source = 'Local'
    elif isinstance(raw, dict) and raw.get('source') == 'Partner API':
        source = 'Partner API'
    try:
        student = save_student(data, source)
        return jsonify({'message': 'Student added successfully!', 'id': student['id'], 'student': student}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'This student ID already exists.'}), 409


@app.route('/students/<int:id>', methods=['GET'])
@app.route('/api/students/<int:id>', methods=['GET'])
def get_student_by_id(id):
    with get_db_connection() as conn:
        student = conn.execute('SELECT * FROM students WHERE id=?', (id,)).fetchone()
    if student is None:
        return jsonify({'error': 'Student not found.'}), 404
    return jsonify(dict(student))


@app.route('/api/students/<int:id>', methods=['PUT'])
def update_student(id):
    data, error = validate_student(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400
    try:
        with get_db_connection() as conn:
            cursor = conn.execute('''UPDATE students SET student_id=?, name=?, program=?, year=?, section=? WHERE id=?''',
                                  (data['student_id'], data['name'], data['program'], data['year'], data['section'], id))
            if cursor.rowcount == 0:
                return jsonify({'error': 'Student not found.'}), 404
            student = dict(conn.execute('SELECT * FROM students WHERE id=?', (id,)).fetchone())
        return jsonify({'message': 'Student updated successfully!', 'student': student})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'This student ID already exists.'}), 409


@app.route('/api/students/<int:id>', methods=['DELETE'])
def delete_student(id):
    with get_db_connection() as conn:
        cursor = conn.execute('DELETE FROM students WHERE id=?', (id,))
        if cursor.rowcount == 0:
            return jsonify({'error': 'Student not found.'}), 404
    return jsonify({'message': 'Student deleted successfully!'})


@app.route('/students/program/<program>')
def get_students_by_program(program):
    with get_db_connection() as conn:
        students = [dict(r) for r in conn.execute('SELECT * FROM students WHERE LOWER(program)=LOWER(?) ORDER BY name', (program,))]
    return jsonify({'program': program, 'count': len(students), 'students': students})


@app.route('/students/year/<int:year>')
def get_students_by_year(year):
    if year not in (1, 2, 3, 4):
        return jsonify({'error': 'Year must be between 1 and 4.'}), 400
    with get_db_connection() as conn:
        students = [dict(r) for r in conn.execute('SELECT * FROM students WHERE year=? ORDER BY name', (year,))]
    return jsonify({'year': year, 'count': len(students), 'students': students})


@app.route('/partner-records')
@app.route('/api/classmate')
def partner_records():
    result, error, status = partner_request('GET')
    if error:
        return jsonify({'error': error}), status
    if isinstance(result, dict):
        result = result.get('students', [])
    if not isinstance(result, list):
        return jsonify({'error': 'Partner API returned an unexpected data format.'}), 502
    return jsonify(result)


@app.route('/import-student', methods=['POST'])
def import_student():
    data, error = validate_student(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400
    try:
        student = save_student(data, 'Classmate API')
        return jsonify({'message': 'Remote record saved', 'student': student}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Student ID already exists in your database.'}), 409


@app.route('/send-partner-record', methods=['POST'])
def send_partner_record():
    data, error = validate_student(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400
    data['source'] = 'Partner API'
    result, error, status = partner_request('POST', data)
    if error:
        return jsonify({'error': error}), status
    return jsonify({'message': 'Practice record sent to partner successfully.', 'partner_response': result}), 200


ensure_database()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
