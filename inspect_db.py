import sqlite3
import sys

DB_PATH = "data/trainer.db"
TABLES = ["users", "exercises", "workouts", "workout_sets", "injuries"]


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("== Conteo de filas por tabla ==")
    for table in TABLES:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:14} {count}")

    table = sys.argv[1] if len(sys.argv) > 1 else "exercises"
    if table not in TABLES:
        print(f"\nTabla desconocida: {table}. Opciones: {TABLES}")
        return

    print(f"\n== Contenido de '{table}' ==")
    for row in conn.execute(f"SELECT * FROM {table}"):
        print(dict(row))


if __name__ == "__main__":
    main()