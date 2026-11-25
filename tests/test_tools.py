import sqlite3
import pytest

from src.trainer.repository import (
    add_exercise,
    add_injury,
    add_user,
    get_active_injuries,
    get_recent_workouts,
)
from src.trainer.tools import TOOLS, execute_tool
from src.trainer.llm import to_gemini_tool

def seed(conn: sqlite3.Connection) -> int:
    user_id = add_user(conn, "Ana", "ganar masa muscular", 3, "mancuernas")
    add_exercise(conn, "Sentadilla goblet", "piernas", "mancuernas", "principiante")
    add_exercise(conn, "Flexiones", "pecho", "peso corporal", "principiante")
    return user_id


def test_search_exercises_filters_by_muscle_group(conn: sqlite3.Connection) -> None:
    user_id = seed(conn)
    result = execute_tool(conn, user_id, "search_exercises", {"muscle_group": "Piernas"})
    names = [e["name"] for e in result["exercises"]]
    assert names == ["Sentadilla goblet"]


def test_get_user_profile_includes_active_injuries(conn: sqlite3.Connection) -> None:
    user_id = seed(conn)
    add_injury(conn, user_id, "dolor de rodilla")
    result = execute_tool(conn, user_id, "get_user_profile", {})
    assert result["name"] == "Ana"
    assert result["active_injuries"] == ["dolor de rodilla"]


def test_log_workout_saves_sets_and_returns_summary(conn: sqlite3.Connection) -> None:
    user_id = seed(conn)
    result = execute_tool(
        conn,
        user_id,
        "log_workout",
        {
            "performed_on": "2026-11-16",
            "sets": [{"exercise_name": "sentadilla goblet", "reps": 10, "weight_kg": 20}],
        },
    )
    assert "error" not in result
    assert result["total_sets"] == 1
    assert get_recent_workouts(conn, user_id)[0].volume_kg == 200.0


def test_log_workout_unknown_exercise_saves_nothing(conn: sqlite3.Connection) -> None:
    user_id = seed(conn)
    result = execute_tool(
        conn,
        user_id,
        "log_workout",
        {"sets": [{"exercise_name": "Ejercicio inventado", "reps": 10, "weight_kg": 20}]},
    )
    assert "error" in result
    assert get_recent_workouts(conn, user_id) == []


def test_log_workout_invalid_date_returns_error(conn: sqlite3.Connection) -> None:
    user_id = seed(conn)
    result = execute_tool(
        conn,
        user_id,
        "log_workout",
        {
            "performed_on": "ayer",
            "sets": [{"exercise_name": "Flexiones", "reps": 10, "weight_kg": 0}],
        },
    )
    assert "error" in result


def test_report_injury_is_saved_with_consent(conn: sqlite3.Connection) -> None:
    user_id = seed(conn)
    result = execute_tool(
        conn,
        user_id,
        "report_injury",
        {"description": "hombro derecho", "user_confirmed": True},
        user_message="Si, registrala",
    )
    assert result["saved"] is True
    assert get_active_injuries(conn, user_id) == ["hombro derecho"]

def test_report_injury_without_confirmation_flag_is_blocked(conn: sqlite3.Connection) -> None:
    user_id = seed(conn)
    result = execute_tool(
        conn, user_id, "report_injury", {"description": "hombro derecho"}, user_message="Sí"
    )
    assert "consentimiento" in result["error"]
    assert get_active_injuries(conn, user_id) == []


def test_unknown_tool_returns_error(conn: sqlite3.Connection) -> None:
    result = execute_tool(conn, 1, "borrar_todo", {})
    assert "error" in result

@pytest.mark.parametrize(
    "user_message",
    ["No, no la registres", "Me duele la rodilla derecha hoy", "Quizás luego"],
)
def test_report_injury_is_blocked_without_clear_acceptance(
    conn: sqlite3.Connection, user_message: str
) -> None:
    user_id = seed(conn)
    result = execute_tool(
        conn,
        user_id,
        "report_injury",
        {"description": "rodilla", "user_confirmed": True},
        user_message=user_message,
    )
    assert "error" in result
    assert get_active_injuries(conn, user_id) == []

@pytest.mark.parametrize(("reps", "weight"), [(5000, 20.0), (10, 900.0)])
def test_log_workout_rejects_absurd_values(
    conn: sqlite3.Connection, reps: int, weight: float
) -> None:
    user_id = seed(conn)
    result = execute_tool(
        conn,
        user_id,
        "log_workout",
        {"sets": [{"exercise_name": "Flexiones", "reps": reps, "weight_kg": weight}]},
    )
    assert "fuera de rango" in result["error"]
    assert get_recent_workouts(conn, user_id) == []

def test_no_tool_lets_the_model_choose_the_user(conn: sqlite3.Connection) -> None:
    for tool in TOOLS:
        properties = (tool.parameters or {}).get("properties", {})
        assert "user_id" not in properties

def test_gemini_conversion_accepts_all_tools() -> None:
    gemini_tool = to_gemini_tool(TOOLS)
    declared = [d.name for d in gemini_tool.function_declarations or []]
    assert declared == [tool.name for tool in TOOLS]

def test_log_workout_missing_reps_returns_clear_error(conn: sqlite3.Connection) -> None:
    user_id = seed(conn)
    result = execute_tool(
        conn,
        user_id,
        "log_workout",
        {"sets": [{"exercise_name": "Sentadilla goblet", "weight_kg": 20}]},
    )
    assert "reps" in result["error"]
    assert get_recent_workouts(conn, user_id) == []