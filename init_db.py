import os
import sqlite3
from pathlib import Path

DATABASE = Path(os.environ.get("DATABASE_PATH", str(Path(__file__).resolve().parent / "students.db")))

def initialize_database():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    try:
        connection.execute("""CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            program TEXT NOT NULL,
            year INTEGER NOT NULL,
            section TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'Local'
        )""")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(students)")}
        if "source" not in columns:
            connection.execute("ALTER TABLE students ADD COLUMN source TEXT NOT NULL DEFAULT 'Local'")
        connection.execute("UPDATE students SET source='Local' WHERE source IS NULL OR TRIM(source) = ''")
        connection.commit()
        print("Lab 9 SQLite database ready:", DATABASE)
        print("Existing student records preserved.")
        for source, count in connection.execute("SELECT source, COUNT(*) FROM students GROUP BY source"):
            print(f"{source}: {count}")
    finally:
        connection.close()

if __name__ == '__main__':
    initialize_database()
