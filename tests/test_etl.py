import sqlite3
from pathlib import Path

from src.trainer.etl import run_etl, transform

def test_transform_normalizes_and_rejects_duplicates() -> None:
    rows = [
        {"name": " sentadilla goblet ", "muscle_group": "Piernas",
         "equipment": "Mancuernas", "difficulty": "Principiante"},
        {"name": "Sentadilla Goblet", "muscle_group": "piernas",
         "equipment": "mancuernas", "difficulty": "principiante"},
    ]
    valid, errors = transform(rows)
    assert len(valid) == 1
    assert valid[0].name == "Sentadilla goblet"
    assert valid[0].muscle_group == "piernas"
    assert len(errors) == 1

def test_transform_rejercts_invalid_difficulty() -> None:
    rows = [{"name": "Dominadas", "muscle_group": "espalda",
             "equipment": "barra", "difficulty": "experto"}]
    valid, errors = transform(rows)
    assert valid == []
    assert "invalid difficulty" in errors[0]

def test_run_etl_is_idempotent(conn: sqlite3.Connection, tmp_path: Path) -> None:
    csv_file = tmp_path / "exercises.csv"
    csv_file.write_text(
        "name,muscle_group,equipment,difficulty\n"
        "Plancha,core,peso corporal,principiante\n",
        encoding="utf-8",
    )
    first = run_etl(conn, csv_file)
    second = run_etl(conn, csv_file)
    assert first.inserted == 1
    assert second.inserted == 0

