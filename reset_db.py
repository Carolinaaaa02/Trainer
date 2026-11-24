import sqlite3

DB_PATH = "data/trainer.db"
# El orden importa: primero las tablas que dependen de otras (llaves foráneas).
USER_TABLES = ["workout_sets", "workouts", "injuries", "users"]


def main() -> None:
    answer = input("Esto borra usuarios, entrenamientos y lesiones. ¿Seguro? (s/n): ")
    if answer.strip().lower() != "s":
        print("Cancelado.")
        return

    conn = sqlite3.connect(DB_PATH)
    with conn:
        for table in USER_TABLES:
            conn.execute(f"DELETE FROM {table}")
        placeholders = ",".join("?" * len(USER_TABLES))
        conn.execute(
            f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})", USER_TABLES
        )
    conn.close()
    print("Listo. El catálogo de ejercicios se conservó.")


if __name__ == "__main__":
    main()