import csv
from pathlib import Path

with Path("data/exercises.csv").open(encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)
    print("Columnas detectadas:", reader.fieldnames)
    print("Primera fila:", next(reader))