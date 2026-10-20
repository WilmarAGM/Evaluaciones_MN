"""Migración idempotente: agrega exams.review_open. Los exámenes que ya
existían quedan con la revisión HABILITADA (sus estudiantes ya veían la nota
al terminar; ocultársela de golpe sería quitarles algo). Los exámenes nuevos
nacen con la revisión cerrada. La tabla review_requests es nueva y la crea
create_all.

Uso: python -m app.migrate_review <ruta_a_la_bd.db>
"""
import sqlite3
import sys


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    existing = [row[1] for row in cur.execute("PRAGMA table_info(exams)")]
    if not existing:
        print(f"[{db_path}] Tabla exams no existe; nada que migrar.")
    elif "review_open" in existing:
        print(f"[{db_path}] exams.review_open ya existía.")
    else:
        cur.execute("ALTER TABLE exams ADD COLUMN review_open BOOLEAN NOT NULL DEFAULT 0")
        cur.execute("UPDATE exams SET review_open = 1")
        print(f"[{db_path}] exams.review_open agregada; {cur.rowcount} examen(es) existentes con revisión habilitada.")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m app.migrate_review <ruta_a_la_bd.db>")
        sys.exit(1)
    migrate(sys.argv[1])
