"""Migración idempotente: agrega problem_banks.is_global (bancos generales
gestionados por el admin, visibles en solo lectura para todos los docentes al
armar un examen, sin importar su grupo). Bases sembradas antes de esto quedan
con is_global=0 en todos sus bancos existentes (siguen siendo bancos
personales de grupo, comportamiento idéntico a antes).

Uso: python -m app.migrate_global_banks <ruta_a_la_bd.db>
"""
import sqlite3
import sys

MIGRATIONS = [
    (
        "problem_banks",
        "PRAGMA table_info(problem_banks)",
        [
            ("is_global", "ALTER TABLE problem_banks ADD COLUMN is_global BOOLEAN NOT NULL DEFAULT 0"),
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
        print("Uso: python -m app.migrate_global_banks <ruta_a_la_bd.db>")
        sys.exit(1)
    migrate(sys.argv[1])
