"""Migración idempotente: introduce ProblemBank + ExamProblem (tabla puente)
reemplazando el acople directo Problem.exam_id/Problem.order.

Para cada examen existente crea (si no existe ya) un ProblemBank con el mismo
título, mueve sus problemas a ese banco (bank_id) y crea las filas
ExamProblem correspondientes preservando el orden original. Las columnas
viejas problems.exam_id / problems.order quedan huérfanas en la tabla pero
sin uso (SQLite no soporta DROP COLUMN de forma directa en versiones viejas;
no estorban).

Uso: python -m app.migrate_problem_banks <ruta_a_la_bd.db>
"""
import sqlite3
import sys


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    exam_cols = [row[1] for row in cur.execute("PRAGMA table_info(exams)")]
    if "is_open" not in exam_cols:
        # DEFAULT 1 (abierto): preserva el comportamiento actual de exámenes ya
        # existentes, que no tenían control de habilitación y eran accesibles
        # libremente.
        cur.execute("ALTER TABLE exams ADD COLUMN is_open BOOLEAN NOT NULL DEFAULT 1")
        print(f"[{db_path}] Columna exams.is_open agregada (default abierto).")
    else:
        print(f"[{db_path}] Columna exams.is_open ya existía.")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS problem_banks (
            id INTEGER PRIMARY KEY,
            title VARCHAR NOT NULL,
            description TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS exam_problems (
            id INTEGER PRIMARY KEY,
            exam_id INTEGER NOT NULL,
            problem_id INTEGER NOT NULL,
            "order" INTEGER DEFAULT 0,
            UNIQUE(exam_id, problem_id)
        )
        """
    )

    cols = [row[1] for row in cur.execute("PRAGMA table_info(problems)")]
    if "bank_id" not in cols:
        cur.execute("ALTER TABLE problems ADD COLUMN bank_id INTEGER")
        print(f"[{db_path}] Columna problems.bank_id agregada.")
    else:
        print(f"[{db_path}] Columna problems.bank_id ya existía.")

    has_exam_id = "exam_id" in cols
    if not has_exam_id:
        print(f"[{db_path}] problems.exam_id ya no existe: nada que migrar (esquema ya migrado).")
        conn.commit()
        conn.close()
        return

    exams = cur.execute("SELECT id, title FROM exams").fetchall()
    for exam_id, exam_title in exams:
        bank_row = cur.execute("SELECT id FROM problem_banks WHERE title = ?", (exam_title,)).fetchone()
        if bank_row:
            bank_id = bank_row[0]
        else:
            cur.execute(
                "INSERT INTO problem_banks (title, description) VALUES (?, ?)",
                (exam_title, f"Migrado automáticamente desde el examen '{exam_title}'."),
            )
            bank_id = cur.lastrowid
            print(f"[{db_path}] Banco '{exam_title}' creado (id={bank_id}).")

        problems = cur.execute(
            'SELECT id, "order" FROM problems WHERE exam_id = ?', (exam_id,)
        ).fetchall()
        for problem_id, order in problems:
            cur.execute("UPDATE problems SET bank_id = ? WHERE id = ?", (bank_id, problem_id))
            cur.execute(
                "INSERT OR IGNORE INTO exam_problems (exam_id, problem_id, \"order\") VALUES (?, ?, ?)",
                (exam_id, problem_id, order or 0),
            )
        print(f"[{db_path}] {len(problems)} problema(s) del examen '{exam_title}' migrados a bank_id={bank_id}.")

    # SQLite no soporta relajar/quitar un NOT NULL con ALTER TABLE, así que
    # reconstruimos la tabla sin las columnas legadas exam_id/order (sus datos
    # ya quedaron copiados en exam_problems arriba).
    cur.execute(
        """
        CREATE TABLE problems_new (
            id INTEGER PRIMARY KEY,
            bank_id INTEGER NOT NULL,
            title VARCHAR NOT NULL,
            statement_md TEXT NOT NULL,
            starter_code TEXT NOT NULL,
            rubric TEXT,
            solution_code TEXT
        )
        """
    )
    cur.execute(
        """
        INSERT INTO problems_new (id, bank_id, title, statement_md, starter_code, rubric, solution_code)
        SELECT id, bank_id, title, statement_md, starter_code, rubric, solution_code FROM problems
        """
    )
    cur.execute("DROP TABLE problems")
    cur.execute("ALTER TABLE problems_new RENAME TO problems")
    print(f"[{db_path}] Tabla problems reconstruida sin exam_id/order legados.")

    conn.commit()
    conn.close()
    print(f"[{db_path}] Migración a ProblemBank/ExamProblem completada.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m app.migrate_problem_banks <ruta_a_la_bd.db>")
        sys.exit(1)
    migrate(sys.argv[1])
