"""Migración idempotente: reemplaza la restricción única (attempt_id, slot_id)
de attempt_problems por (attempt_id, problem_id). La anterior impedía que un
slot aleatorio con count >= 2 asignara más de un problema del mismo banco
(IntegrityError al abrir el examen). SQLite no permite quitar una restricción
con ALTER TABLE, así que se reconstruye la tabla conservando todos los datos.

Uso: python -m app.migrate_attempt_problems <ruta_a_la_bd.db>
"""
import sqlite3
import sys


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    row = cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='attempt_problems'").fetchone()
    if row is None:
        print(f"[{db_path}] Tabla attempt_problems no existe; nada que migrar (create_all la creará bien).")
    elif "uq_attempt_slot" not in row[0]:
        print(f"[{db_path}] attempt_problems ya usa la restricción nueva.")
    else:
        cur.executescript(
            """
            BEGIN;
            CREATE TABLE attempt_problems_new (
                id INTEGER NOT NULL PRIMARY KEY,
                attempt_id INTEGER NOT NULL REFERENCES exam_attempts (id),
                slot_id INTEGER NOT NULL REFERENCES exam_slots (id),
                problem_id INTEGER NOT NULL REFERENCES problems (id),
                "order" INTEGER,
                CONSTRAINT uq_attempt_problem UNIQUE (attempt_id, problem_id)
            );
            INSERT INTO attempt_problems_new (id, attempt_id, slot_id, problem_id, "order")
                SELECT id, attempt_id, slot_id, problem_id, "order" FROM attempt_problems;
            DROP TABLE attempt_problems;
            ALTER TABLE attempt_problems_new RENAME TO attempt_problems;
            CREATE INDEX ix_attempt_problems_id ON attempt_problems (id);
            COMMIT;
            """
        )
        n = cur.execute("SELECT COUNT(*) FROM attempt_problems").fetchone()[0]
        print(f"[{db_path}] Restricción reemplazada por (attempt_id, problem_id); {n} filas conservadas.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m app.migrate_attempt_problems <ruta_a_la_bd.db>")
        sys.exit(1)
    migrate(sys.argv[1])
