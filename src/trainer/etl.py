import csv
import sqlite3
from idlelib.iomenu import errors

import _sqlite3
from dataclasses import dataclass
from pathlib import Path

from src.trainer.db import connect, init_db

VALID_DIFICULTIES = {"principiante", "intermedio", "avanzado"}

@dataclass(frozen=True)
class ExerciseRow:
    name: str
    muscle_group: str
    equipment: str
    difficulty: str

@dataclass(frozen= True)
class EtlResult:
    inserted: int
    rejected: list[str]

def extract(csv_path: Path) -> list[dict[str, str]]:
    "E: Read the CSV as is"
    with csv_path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))

def transform(rows: list[dict[str, str]]) -> tuple[list[ExerciseRow], list[str]]:
    "T: cleans, validates, and removes duplicates. Returns (valid items, errors)"
    valid: list[ExerciseRow] = []
    errors: list[str] = []
    seen: set[str] = set()

    for line, row in enumerate(rows, start=2):
        name = " ".join((row.get("name") or "").split()).capitalize()
        muscle_group = (row.get("muscle_group") or "").strip().lower()
        equipment = (row.get("equipment") or "").strip().lower()
        difficulty = (row.get("difficulty") or "").strip().lower()

        if not name or not muscle_group or not equipment:
            errors.append(f"line {line}: required fields are missing")
            continue
        if difficulty not in VALID_DIFICULTIES:
            errors.append(f"line {line}: invalid difficulty '{difficulty}'")
            continue
        if name.lower() in seen:
            errors.append(f"line {line}: duplicate '{name}'")
            continue

        seen.add(name.lower())
        valid.append(ExerciseRow(name, muscle_group, equipment, difficulty))

    return valid, errors

def load(conn: _sqlite3.Connection, exercises: list[ExerciseRow]) -> int:
    "L: Inserts into the database. Ignores those that already exist"
    cursor = conn.executemany(
        "INSERT OR IGNORE INTO exercises (name, muscle_group, equipment, difficulty) "
        "VALUES (?, ?, ?, ?)",
        [(e.name, e.muscle_group, e.equipment, e.difficulty) for e in exercises],
    )
    conn.commit()
    return cursor.rowcount

def run_etl(conn: sqlite3.Connection, csv_path) -> EtlResult:
    valid, errors = transform(extract(csv_path))
    inserted = load(conn, valid)
    return EtlResult(inserted=inserted, rejected=errors)

if __name__ == "__main__":
    connection = connect()
    init_db(connection)
    result = run_etl(connection, Path("data/exercises.csv"))
    print(f"Inserted: {result.inserted}")
    for message in result.rejected:
        print(f"Rejected:", message)
