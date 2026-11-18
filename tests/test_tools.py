import sqlite3

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


def test_report_injury_is_saved(conn: sqlite3.Connection) -> None:
    user_id = seed(conn)
    result = execute_tool(conn, user_id, "report_injury", {"description": "hombro derecho"})
    assert result["saved"] is True
    assert get_active_injuries(conn, user_id) == ["hombro derecho"]


def test_unknown_tool_returns_error(conn: sqlite3.Connection) -> None:
    result = execute_tool(conn, 1, "borrar_todo", {})
    assert "error" in result


def test_no_tool_lets_the_model_choose_the_user(conn: sqlite3.Connection) -> None:
    for tool in TOOLS:
        properties = (tool.parameters or {}).get("properties", {})
        assert "user_id" not in properties

def test_gemini_conversion_accepts_all_tools() -> None:
    gemini_tool = to_gemini_tool(TOOLS)
    declared = [d.name for d in gemini_tool.function_declarations or []]
    assert declared == [tool.name for tool in TOOLS]