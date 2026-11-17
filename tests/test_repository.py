import sqlite3
from collections.abc import Iterator
from datetime import date

import pytest

from src.trainer.repository import (
    SetEntry,
    add_exercise,
    add_injury,
    add_user,
    find_exercises,
    get_active_injuries,
    get_recent_workouts,
    get_user,
    log_workout
)

def test_add_and_get_user(conn: sqlite3.Connection) -> None:
    user_id = add_user(conn, "Ana", "ganar masa muscular", 3, "mancuernas")
    user = get_user(conn, user_id)
    assert user is not None
    assert user.name == "Ana"
    assert user.days_per_week == 3

def test_get_user_missing_returns_none(conn: sqlite3.Connection) -> None:
    assert get_user(conn, 999) is None

def test_invalid_days_per_week_is_rejected(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        add_user(conn, "Ana", "ganar masa muscular", 9, "mancuernas")

def test_active_injuries(conn: sqlite3.Connection) -> None:
    user_id = add_user(conn, "Ana", "fuerza", 3, "mancuernas")
    add_injury(conn, user_id, "dolor de rodilla izquierda")
    assert get_active_injuries(conn, user_id) == ["dolor de rodilla izquierda"]

def test_find_exercises_filters_by_muscle_group(conn: sqlite3.Connection) -> None:
    add_exercise(conn, "Sentadilla goblet", "piernas", "mancuernas", "principiante")
    add_exercise(conn, "Flexiones", "pecho", "peso corporal", "principiante")
    result = find_exercises(conn, muscle_group="piernas")
    assert [e.name for e in result] == ["Sentadilla goblet"]

def test_log_workout_computes_sets_and_volume(conn: sqlite3.Connection) -> None:
    user_id = add_user(conn, "Ana", "fuerza", 3, "mancuernas")
    exercise_id = add_exercise(conn, "Curl de biceps", "brazos", "mancuernas", "principiante")
    log_workout(
        conn,
        user_id,
        date(2026, 11, 9),
        [SetEntry(exercise_id, 10, 20.0), SetEntry(exercise_id, 8, 25.0)],
    )
    summaries = get_recent_workouts(conn, user_id)
    assert len(summaries) == 1
    assert summaries[0].total_sets == 2
    assert summaries[0].volume_kg == 400.0