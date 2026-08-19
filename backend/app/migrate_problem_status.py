"""Migración idempotente: agrega problems.status (default 'published') y
problems.review_notes a bases de datos sembradas antes de que existiera el
pipeline de carga con agentes IA (ver load_problems_from_tex.py). Todo
problema existente queda 'published' (comportamiento igual al de antes de
esta columna), con review_notes NULL (nunca auditado).

Uso: python -m app.migrate_problem_status <ruta_a_la_bd.db>
"""
import sqlite3
import sys


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cols = [row[1] for row in cur.execute("PRAGMA table_info(problems)")]
    if "status" not in cols:
        cur.execute("ALTER TABLE problems ADD COLUMN status TEXT NOT NULL DEFAULT 'published'")
        print(f"[{db_path}] Columna status agregada (todos los problemas existentes quedan 'published').")
    else:
        print(f"[{db_path}] Columna status ya existía.")

    if "review_notes" not in cols:
        cur.execute("ALTER TABLE problems ADD COLUMN review_notes TEXT")
        print(f"[{db_path}] Columna review_notes agregada.")
    else:
        print(f"[{db_path}] Columna review_notes ya existía.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m app.migrate_problem_status <ruta_a_la_bd.db>")
        sys.exit(1)
    migrate(sys.argv[1])
