"""Migración idempotente para pasar de un solo docente a 4 grupos aislados:

1. Agrega la columna `group` (INTEGER) a students, exams y problem_banks si no existe.
   ("group" es palabra reservada en SQL, se referencia entre comillas dobles).
2. Pone group = 1 en todos los estudiantes (role='student'), exámenes y bancos
   existentes (se asume que todo lo sembrado hasta ahora es del Grupo 1).
3. Convierte la cuenta wagonzalezm@unal.edu.co de "teacher" a "admin" (group = NULL).

Uso: python -m app.migrate_groups <ruta_a_la_bd.db>
"""
import sqlite3
import sys

ADMIN_EMAIL = "wagonzalezm@unal.edu.co"


def _ensure_group_column(cur, table: str):
    cols = [row[1] for row in cur.execute(f"PRAGMA table_info({table})")]
    if "group" not in cols:
        cur.execute(f'ALTER TABLE {table} ADD COLUMN "group" INTEGER')
        print(f"[{table}] columna group agregada.")
    else:
        print(f"[{table}] columna group ya existía.")


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    for table in ("students", "exams", "problem_banks"):
        _ensure_group_column(cur, table)

    n = cur.execute('UPDATE students SET "group" = 1 WHERE role = ? AND "group" IS NULL', ("student",)).rowcount
    print(f"students (role=student): {n} puestos en group=1.")

    n = cur.execute('UPDATE exams SET "group" = 1 WHERE "group" IS NULL').rowcount
    print(f"exams: {n} puestos en group=1.")

    n = cur.execute('UPDATE problem_banks SET "group" = 1 WHERE "group" IS NULL').rowcount
    print(f"problem_banks: {n} puestos en group=1.")

    row = cur.execute("SELECT id, role FROM students WHERE email = ?", (ADMIN_EMAIL,)).fetchone()
    if row is None:
        print(f"AVISO: no existe ninguna cuenta con email {ADMIN_EMAIL}; no se creó ningún admin.")
    elif row[1] == "admin":
        print(f"{ADMIN_EMAIL} ya era admin.")
    else:
        cur.execute('UPDATE students SET role = ?, "group" = NULL WHERE id = ?', ("admin", row[0]))
        print(f"{ADMIN_EMAIL} convertido de '{row[1]}' a 'admin'.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m app.migrate_groups <ruta_a_la_bd.db>")
        sys.exit(1)
    migrate(sys.argv[1])
