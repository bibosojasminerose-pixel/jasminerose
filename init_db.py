
import sqlite3
from pathlib import Path

DATABASE = Path(__file__).resolve().parent / "students.db"


def initialize_database():
    connection = sqlite3.connect(DATABASE)

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                program TEXT NOT NULL,
                year INTEGER NOT NULL,
                section TEXT NOT NULL
            )
        """)

        connection.commit()

        print("SQLite database initialized successfully!")
        print("Database:", DATABASE)
        print("Existing records have been preserved.")

    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
