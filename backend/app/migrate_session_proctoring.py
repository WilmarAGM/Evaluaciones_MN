"""Migración idempotente: agrega las columnas de sesión única por estudiante
(students.session_id / device_id / last_seen) y del control de salidas de
ventana (exams.max_violations; exam_attempts.violations / violation_log /
annulled_at / annul_reason) a bases sembradas antes de esas funciones.

Los exámenes existentes quedan con max_violations = 0 (control desactivado),
o sea, se comportan exactamente igual que antes. Si una tabla todavía no
existe (base nueva) no hace nada: create_all la creará con las columnas.

Uso: python -m app.migrate_session_proctoring <ruta_a_la_bd.db>
"""
import sqlite3
import sys

# (tabla, sentencia PRAGMA, [(columna, sentencia ALTER)]). Todo literal: los
# identificadores SQL no se pueden parametrizar y aquí no entra nada externo.
MIGRATIONS = [
    (
        "students",
        "PRAGMA table_info(students)",
        [
            ("session_id", "ALTER TABLE students ADD COLUMN session_id TEXT"),
            ("device_id", "ALTER TABLE students ADD COLUMN device_id TEXT"),
            ("last_seen", "ALTER TABLE students ADD COLUMN last_seen DATETIME"),
        ],
    ),
    (
        "exams",
        "PRAGMA table_info(exams)",
        [
            ("max_violations", "ALTER TABLE exams ADD COLUMN max_violations INTEGER NOT NULL DEFAULT 0"),
        ],
    ),
    (
        "exam_attempts",
        "PRAGMA table_info(exam_attempts)",
        [
            ("violations", "ALTER TABLE exam_attempts ADD COLUMN violations INTEGER NOT NULL DEFAULT 0"),
            ("violation_log", "ALTER TABLE exam_attempts ADD COLUMN violation_log TEXT NOT NULL DEFAULT '[]'"),
            ("annulled_at", "ALTER TABLE exam_attempts ADD COLUMN annulled_at DATETIME"),
            ("annul_reason", "ALTER TABLE exam_attempts ADD COLUMN annul_reason TEXT"),
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
        print("Uso: python -m app.migrate_session_proctoring <ruta_a_la_bd.db>")
        sys.exit(1)
    migrate(sys.argv[1])
