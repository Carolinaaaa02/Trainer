import sqlite3
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date
from logging import Handler
from typing import Any

from src.trainer.guardrails import is_affirmative
from src.trainer import repository as repo

JsonDict = dict[str, Any]
Guard = Callable[[str, JsonDict], str | None]
Handler = Callable[[sqlite3.Connection, int, JsonDict], JsonDict]

MAX_SETS_PER_WORKOUT = 30
MAX_REPS = 100
MAX_WEIGHT_KG = 500.0

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: JsonDict | None
    handler: Handler
    guard: Guard | None = None

def _search_exercises(conn: sqlite3.Connection, user_id: int, args: JsonDict) -> JsonDict:
    muscle = args.get("muscle_group")
    equipment = args.get("equipment")
    exercises = repo.find_exercises(
        conn,
        muscle_group=str(muscle).strip().lower() if muscle else None,
        equipment=str(equipment).strip().lower() if equipment else None,
    )
    return {
        "exercises": [
            {"name": e.name, "muscle_group": e.muscle_group,
             "equipment": e.equipment, "difficulty": e.difficulty}
            for e in exercises
        ]
    }

def _get_profile(conn: sqlite3.Connection, user_id: int, arg: JsonDict) -> JsonDict:
    user = repo.get_user(conn, user_id)
    if user is None:
        return {"error": "Usuario no encontrado"}
    return {
        "name": user.name,
        "goal": user.goal,
        "days_per_week": user.days_per_week,
        "equipment": user.equipment,
        "active_injuries": repo.get_active_injuries(conn, user_id),
    }

def _get_recent_workouts(conn: sqlite3.Connection, user_id: int, args: JsonDict) -> JsonDict:
    limit = max(1, min(int(args.get("limit", 5)), 20))
    workouts = repo.get_recent_workouts(conn, user_id, limit)
    return {"workouts": [asdict(w) for w in workouts]}

def _log_workout(conn: sqlite3.Connection, user_id: int, args: JsonDict) -> JsonDict:
    raw_sets = args["sets"]
    if not raw_sets:
        return {"error": "Debes enviar al menos una serie"}

    performed_on = (
        date.fromisoformat(str(args["performed_on"]))
        if args.get("performed_on")
        else date.today()
    )

    entries: list[repo.SetEntry] = []
    unknown: list[str] = []
    for index, raw in enumerate(raw_sets, start=1):
        missing = [k for k in ("exercise_name", "reps", "weight_kg") if raw.get(k) is None]
        if missing:
            return {
                "error": f"Serie {index}: faltan los campos {missing}. "
                         "No inventes valores: pregunta al usuario por los datos que faltan."
            }
        name = str(raw["exercise_name"])
        exercise = repo.get_exercise_by_name(conn, name)
        if exercise is None:
            unknown.append(name)
            continue
        reps = int(raw["reps"])
        weight = float(raw["weight_kg"])
        if not 0 < reps <= MAX_REPS or not 0 <= weight <= MAX_WEIGHT_KG:
            return {
                "error": f"Valores fuera de rango: reps debe estar entre 1 y {MAX_REPS} "
                f"y weight_kg entre 0 y {MAX_WEIGHT_KG}"
                "Confirma los datos con el usuario; no los adivines"
            }
        entries.append(repo.SetEntry(exercise.id, reps, weight))
    if len(raw_sets) > MAX_SETS_PER_WORKOUT:
        return {
            "error": f"Máximo {MAX_SETS_PER_WORKOUT} series por registro."
            "Confirma los datos con el usuario: no los adivines"
        }
    if unknown:
        return {
            "error": f"Ejercicios no encontrados en el catálogo: {unknown}. "
            "Usa search_exercises para ver los nombres válidos."
        }

    workout_id = repo.log_workout(
        conn, user_id, performed_on, entries, notes=str(args.get("notes", ""))
    )
    return {
        "workout_id": workout_id,
        "date": performed_on.isoformat(),
        "total_sets": len(entries),
        "volume_kg": sum(e.reps * e.weight_kg for e in entries),
    }

def _report_injury(conn: sqlite3.Connection, user_id: int, args: JsonDict) -> JsonDict:
    description = str(args["description"]).strip()
    if not description:
        return {"error": "La descripción de la lesión no puede estar vacía"}
    repo.add_injury(conn, user_id, description)
    "Úsala solo después de que el usuario haya aceptado explícitamente que la registres."
    return {"saved": True, "description": description}

def _injury_consent_guard(user_message: str, args: JsonDict) -> str | None:
    if args.get("user_confirmed") is not True:
        return (
            "Falta el consentimiento, pregunta al usuario si quiere que registres"
            "la molestia y llama de nuevo con user_confirmed=true solo si acepta"
        )
    if not is_affirmative(user_message):
        return (
            "El último mensaje del usuario no es una aceptación clara. No registres"
            "la molestia: pregunta si quiere que guardes y espera su respuesta"
        )
    return None

TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="search_exercises",
        description=(
            "Busca ejercicios del catálogo. Úsala antes de proponer o registrar "
            "ejercicios, para usar solo nombres que existan. Ambos filtros son opcionales."
        ),
        parameters={
            "type": "object",
            "properties": {
                "muscle_group": {
                    "type": "string",
                    "description": "Grupo muscular: piernas, pecho, espalda, hombros, brazos o core.",
                },
                "equipment": {
                    "type": "string",
                    "description": "Equipo: mancuernas, peso corporal o barra.",
                },
            },
        },
        handler=_search_exercises,

    ),
    ToolSpec(
        name="get_user_profile",
        description=(
            "Devuelve el perfil del usuario: objetivo, días por semana, equipo "
            "disponible y lesiones activas. Consúltala antes de recomendar un plan."
        ),
        parameters=None,
        handler=_get_profile,
    ),
    ToolSpec(
        name="get_recent_workouts",
        description=(
            "Devuelve los entrenamientos recientes del usuario con número de series "
            "y volumen total en kg (repeticiones x peso)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Cuántos entrenamientos devolver (1 a 20). Por defecto 5.",
                },
            },
        },
        handler=_get_recent_workouts,
    ),
    ToolSpec(
        name="log_workout",
        description=(
            "Registra un entrenamiento realizado, con todas sus series. Solo úsala "
            "cuando el usuario cuente lo que ya hizo y haya dado ejercicio, "
            "repeticiones y peso de cada serie. Si falta algún dato, NO inventes "
            "valores: pregúntaselo al usuario. Los nombres de ejercicio deben "
            "existir en el catálogo."
        ),

        parameters={
            "type": "object",
            "properties": {
                "sets": {
                    "type": "array",
                    "description": "Series realizadas.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "exercise_name": {"type": "string"},
                            "reps": {"type": "integer"},
                            "weight_kg": {
                                "type": "number",
                                "description": "Peso en kg. Usa 0 para peso corporal.",
                            },
                        },
                        "required": ["exercise_name", "reps", "weight_kg"],
                    },
                },
                "performed_on": {
                    "type": "string",
                    "description": "Fecha en formato AAAA-MM-DD. Si se omite, se usa hoy.",
                },
                "notes": {"type": "string", "description": "Notas opcionales."},
            },
            "required": ["sets"],
        },
        handler=_log_workout,
    ),
    ToolSpec(
        name="report_injury",
        description=(
            "Guarda una lesión o molestia para tenerla en cuenta en futuros planes. "
            "No diagnostica ni da tratamiento. Úsala SOLO si en su último mensaje el "
            "usuario aceptó explícitamente que la registres; en ese caso envía "
            "user_confirmed=true. Si no ha aceptado, pregúntale primero."
        ),
        parameters={
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Descripción breve."},
                "user_confirmed": {
                    "type": "boolean",
                    "description": "true solo si el usuario aceptó registrar la molestia"
                },
            },
            "required": ["description", "user_confirmed"]
        },
        handler=_report_injury,
        guard=_injury_consent_guard,
    )
]

TOOLS_BY_NAME: dict[str, ToolSpec] = {tool.name: tool for tool in TOOLS}

def execute_tool(
        conn: sqlite3.Connection,
        user_id: int,
        name:str,
        args: JsonDict,
        user_message: str = "",
) -> JsonDict:
    """Ejecuta una herramienta pedida por el modelo.

    Los errores se devuelven como datos (no como excepciones) para que
    el modelo pueda leerlos y corregirse."""
    spec = TOOLS_BY_NAME.get(name)
    if spec is None:
        return {"error": f"Herramienta desconocida: {name}"}
    if spec.guard is not None:
        problem = spec.guard(user_message, args)
        if problem is not None:
            return {"error": problem}
    try:
        return spec.handler(conn, user_id, args)
    except (KeyError, TypeError, ValueError, sqlite3.Error) as exc:
        return {"error": f"Argumentos inválidos o fallo al ejecutar: {exc!r}"}