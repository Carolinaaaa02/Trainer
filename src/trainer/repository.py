import sqlite3
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class User:
    id: int
    name: str
    goal:str
    days_per_week: str
    equipment: str

@dataclass(frozen=True)
class Exercise:
    id: int
    name:str
    muscle_group: str
    equipment: str
    difficulty: str

@dataclass(frozen=True)
class SetEntry:
    exercise_id:int
    reps: int
    weight_kg: float

@dataclass(frozen=True)
class WorkoutSummary:
    id: int
    performed_on: str
    total_sets: int
    volume_kg: float

def _inserted_id(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise RuntimeError("The insertion did not return an ID")
    return cursor.lastrowid

def add_user (
        conn: sqlite3.Connection,
        name: str,
        goal: str,
        days_per_week: int,
        equipment:str,
) -> int:
    with conn:
        cursor = conn.execute(
            "INSERT INTO users (name, goal, days_per_week, equipment) VALUES (?, ?, ?, ?)",
            (name, goal, days_per_week, equipment),
        )
        return _inserted_id(cursor)

def get_user(conn: sqlite3.Connection, user_id: int) -> User | None:
    row = conn.execute(
        "SELECT id, name, goal, days_per_week, equipment FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return User(**dict(row)) if row else None

def add_exercise(
        conn: sqlite3.Connection,
        name: str,
        muscle_group: str,
        equipment: str,
        difficulty: str,
) -> int:
    with conn:
        cursor = conn.execute(
            "INSERT INTO exercises (name, muscle_group, equipment, difficulty)"
            "VALUES (?, ?, ?, ?)",
            (name, muscle_group, equipment, difficulty),
        )
    return _inserted_id(cursor)

def find_exercises(
    conn: sqlite3.Connection,
    muscle_group: str | None = None,
    equipment: str | None = None,
) -> list[Exercise]:
    query = "SELECT id, name, muscle_group, equipment, difficulty FROM exercises WHERE 1 = 1"
    params: list[str] = []
    if muscle_group is not None:
        query += " AND muscle_group = ?"
        params.append(muscle_group)
    if equipment is not None:
        query += " AND equipment = ?"
        params.append(equipment)
    query += " ORDER BY name"
    rows = conn.execute(query, params).fetchall()
    return [Exercise(**dict(row)) for row in rows]

def add_injury(conn: sqlite3.Connection, user_id: int, description: str) -> int:
    with conn:
        cursor = conn.execute(
            "INSERT INTO injuries (user_id, description) VALUES (?, ?)",
            (user_id, description),
        )
    return _inserted_id(cursor)

def get_active_injuries(conn: sqlite3.Connection, user_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT description FROM injuries WHERE user_id = ? AND active = 1",
        (user_id,),
    ).fetchall()
    return [row["description"] for row in rows]

def log_workout(
    conn: sqlite3.Connection,
        user_id:int,
        performed_on: date,
        sets: list[SetEntry],
        notes: str = "",
) -> int:
    "Save a workout and all its sets in a single transaction"
    with conn:
        cursor = conn.execute(
            "INSERT INTO workouts (user_id, performed_on, notes) VALUES (?, ?, ?)",
            (user_id, performed_on.isoformat(), notes),
        )
        workout_id = _inserted_id(cursor)
        conn.executemany(
            "INSERT INTO workout_sets (workout_id, exercise_id, reps, weight_kg) "
            "VALUES (?, ?, ?, ?)",
            [(workout_id, s.exercise_id , s.reps, s.weight_kg) for s in sets],
        )
    return workout_id

def get_recent_workouts(
    conn: sqlite3.Connection, user_id: int, limit: int = 5
) -> list[WorkoutSummary]:
    rows = conn.execute(
        """
        SELECT w.id AS id,
               w.performed_on AS performed_on,
               COUNT(s.id) AS total_sets,
               COALESCE(SUM(s.reps * s.weight_kg), 0) AS volume_kg
        FROM workouts w
        LEFT JOIN workout_sets s ON s.workout_id = w.id
        WHERE w.user_id = ?
        GROUP BY w.id
        ORDER BY w.performed_on DESC, w.id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return [WorkoutSummary(**dict(row)) for row in rows]



