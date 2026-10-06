"""Migración idempotente: agrega a submissions las columnas de corrección
manual del docente (manual_score, manual_comment, manual_by, manual_at). Las
entregas existentes quedan con manual_score=NULL, o sea con su nota
automática de siempre.

Uso: python -m app.migrate_manual_scores <ruta_a_la_bd.db>
"""
import sqlite3
import sys

MIGRATIONS = [
    (
        "submissions",
        "PRAGMA table_info(submissions)",
        [
            ("manual_score", "ALTER TABLE submissions ADD COLUMN manual_score FLOAT"),
            ("manual_comment", "ALTER TABLE submissions ADD COLUMN manual_comment TEXT"),
            ("manual_by", "ALTER TABLE submissions ADD COLUMN manual_by INTEGER"),
            ("manual_at", "ALTER TABLE submissions ADD COLUMN manual_at DATETIME"),
        ],
    ),
]


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    for table, pragma, alters in MIGRATIONS:
        existing = [row[1] for row in cur.execute(pragma)]
        if not existing:
            print(f"[{db_path}] Tabla {table} no existe; nada que migrar.")
            continue
        for name, alter in alters:
            if name in existing:
                print(f"[{db_path}] {table}.{name} ya existía.")
            else:
                cur.execute(alter)
                print(f"[{db_path}] {table}.{name} agregada.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m app.migrate_manual_scores <ruta_a_la_bd.db>")
        sys.exit(1)
    migrate(sys.argv[1])
