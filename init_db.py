
import sqlite3
from pathlib import Path

DATABASE = Path(__file__).resolve().parent / "students.db"

students = [
    ("2026-00123", "Jasmine Rose Biboso", "BSIT", 3, "A"),
    ("2026-00124", "April Joy Cartangena", "BSIT", 3, "A"),
    ("2026-00125", "Myranie Apura", "BSIT", 3, "A"),
    ("2026-00126", "John Michael Apostol", "BSIT", 3, "A"),
    ("2026-00127", "Student Five", "BSIT", 3, "A")
]

connection = sqlite3.connect(DATABASE)
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    program TEXT NOT NULL,
    year INTEGER NOT NULL,
    section TEXT NOT NULL
)
""")

cursor.executemany("""
INSERT OR IGNORE INTO students
(student_id, name, program, year, section)
VALUES (?, ?, ?, ?, ?)
""", students)

connection.commit()
connection.close()

print("Database initialized successfully!")
print(f"Database location: {DATABASE}")
