"""Migración idempotente para bases de datos ya sembradas (creadas antes de que
existieran duration_minutes=None y Problem.solution_code):

1. Agrega la columna problems.solution_code si no existe.
2. Rellena solution_code de cada problema del examen "Simulacro Parcial Final"
   haciendo match por título contra seed_taller.PROBLEMS.
3. Pone exams.duration_minutes = NULL para ese examen (sin límite de tiempo).

Uso: python -m app.migrate_untimed_solutions <ruta_a_la_bd.db>
"""
import sqlite3
import sys

from .seed_taller import PROBLEMS


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cols = [row[1] for row in cur.execute("PRAGMA table_info(problems)")]
    if "solution_code" not in cols:
        cur.execute("ALTER TABLE problems ADD COLUMN solution_code TEXT")
        print(f"[{db_path}] Columna solution_code agregada.")
    else:
        print(f"[{db_path}] Columna solution_code ya existía.")

    exam_row = cur.execute(
        "SELECT id, duration_minutes FROM exams WHERE title = ?", ("Simulacro Parcial Final",)
    ).fetchone()
    if not exam_row:
        print(f"[{db_path}] No existe el examen 'Simulacro Parcial Final'; nada que migrar.")
        conn.commit()
        conn.close()
        return

    exam_id, duration_minutes = exam_row
    if duration_minutes is not None:
        cur.execute("UPDATE exams SET duration_minutes = NULL WHERE id = ?", (exam_id,))
        print(f"[{db_path}] duration_minutes puesto a NULL (era {duration_minutes}) para exam_id={exam_id}.")
    else:
        print(f"[{db_path}] duration_minutes ya era NULL para exam_id={exam_id}.")

    by_title = {}
    for factory in PROBLEMS:
        data = factory()
        by_title[data["title"]] = data.get("solution_code")

    problems = cur.execute(
        "SELECT id, title, solution_code FROM problems WHERE exam_id = ?", (exam_id,)
    ).fetchall()
    updated, skipped, unmatched = 0, 0, []
    for pid, title, existing_solution in problems:
        solution = by_title.get(title)
        if solution is None:
            unmatched.append(title)
            continue
        if existing_solution == solution:
            skipped += 1
            continue
        cur.execute("UPDATE problems SET solution_code = ? WHERE id = ?", (solution, pid))
        updated += 1

    conn.commit()
    conn.close()
    print(f"[{db_path}] solution_code: {updated} actualizados, {skipped} ya estaban al día.")
    if unmatched:
        print(f"[{db_path}] AVISO — sin match de título (no se tocaron): {unmatched}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m app.migrate_untimed_solutions <ruta_a_la_bd.db>")
        sys.exit(1)
    migrate(sys.argv[1])
