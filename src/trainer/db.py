import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("data/trainer.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    goal TEXT NOT NULL,
    days_per_week INTEGER NOT NULL CHECK (days_per_week BETWEEN 1 AND 7),
    equipment TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    muscle_group TEXT NOT NULL,
    equipment TEXT NOT NULL,
    difficulty TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    performed_on TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS workout_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL REFERENCES workouts(id),
    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
    reps INTEGER NOT NULL CHECK (reps > 0),
    weight_kg REAL NOT NULL CHECK (weight_kg >= 0)
);

CREATE TABLE IF NOT EXISTS injuries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    description TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
"""

def connect(path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    "Open a connection to SQLite. Use ':memory:' for testing"
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    "Create the tables if they do not exist"
    conn.executescript(SCHEMA)
    conn.commit()
