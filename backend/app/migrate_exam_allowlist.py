"""Migración idempotente: agrega exams.restricted (examen habilitado solo para
una lista de documentos, ver models.ExamAllowedStudent). Los exámenes que ya
existen quedan con restricted=0, o sea habilitados para todo su grupo, igual
que antes. La tabla exam_allowed_students es nueva y la crea create_all.

Uso: python -m app.migrate_exam_allowlist <ruta_a_la_bd.db>
"""
import sqlite3
import sys

MIGRATIONS = [
    (
        "exams",
        "PRAGMA table_info(exams)",
        [
            ("restricted", "ALTER TABLE exams ADD COLUMN restricted BOOLEAN NOT NULL DEFAULT 0"),
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
        print("Uso: python -m app.migrate_exam_allowlist <ruta_a_la_bd.db>")
        sys.exit(1)
    migrate(sys.argv[1])
