"""Migración idempotente: las respuestas (submissions) pasan a ser por examen.

Antes había UNA respuesta por (estudiante, problema): si el estudiante
recibía el mismo problema en dos exámenes (bancos compartidos), el segundo
pisaba la respuesta del primero, o no lo dejaba guardar. Ahora la tabla
lleva exam_id y la unicidad es (estudiante, problema, examen).

SQLite no permite cambiar una restricción UNIQUE con ALTER, así que la tabla
se reconstruye con el esquema exacto del modelo actual (models.Submission).

Cada respuesta existente se asigna a TODOS los exámenes del estudiante que
contienen ese problema (por sorteo o lista fija): se copia una vez por
examen. Así ninguna nota cambia al migrar — hasta ahora esa única respuesta
era la que contaba en todos esos exámenes, y en el segundo el estudiante
muchas veces ni podía guardar por el error que esto corrige; dejarla solo en
uno le bajaría la nota del otro por una falla del sistema. De aquí en
adelante cada examen guarda la suya. Las que no corresponden a ningún
intento (pruebas del docente) quedan con exam_id NULL.

Uso: python -m app.migrate_submissions_per_exam <ruta_a_la_bd.db>
"""
import re
import sqlite3
import sys

from sqlalchemy.dialects import sqlite as sqlite_dialect
from sqlalchemy.schema import CreateIndex, CreateTable

from . import models


_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ident(name: str) -> str:
    """Los identificadores (tablas/columnas/índices) no se pueden pasar como
    parámetros en SQLite; vienen del esquema, pero igual se exige que sean
    nombres simples antes de interpolarlos."""
    if not _IDENT.match(name):
        raise ValueError(f"identificador inesperado: {name!r}")
    return name


def _exams_for(cur, student_id, problem_id):
    """Exámenes en los que el estudiante tiene un intento que incluye el problema."""
    rows = cur.execute(
        """
        SELECT a.exam_id FROM attempt_problems ap
          JOIN exam_attempts a ON a.id = ap.attempt_id
         WHERE a.student_id = ? AND ap.problem_id = ?
        UNION
        SELECT a.exam_id FROM exam_problems ep
          JOIN exam_attempts a ON a.exam_id = ep.exam_id
         WHERE a.student_id = ? AND ep.problem_id = ?
        """,
        (student_id, problem_id, student_id, problem_id),
    ).fetchall()
    return sorted(r[0] for r in rows)


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cols = [row[1] for row in cur.execute("PRAGMA table_info(submissions)")]
    if not cols:
        print(f"[{db_path}] Tabla submissions no existe; nada que migrar.")
        return
    if "exam_id" in cols:
        print(f"[{db_path}] submissions.exam_id ya existía.")
        return

    table = models.Submission.__table__
    dialect = sqlite_dialect.dialect()
    before_count = cur.execute("SELECT count(*) FROM submissions").fetchone()[0]

    cur.execute("BEGIN")
    try:
        cur.execute("ALTER TABLE submissions RENAME TO submissions_old")
        for (name,) in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='submissions_old' AND sql IS NOT NULL"
        ).fetchall():
            cur.execute(f'DROP INDEX "{_ident(name)}"')  # nosemgrep
        cur.execute(str(CreateTable(table).compile(dialect=dialect)))
        for index in table.indexes:
            cur.execute(str(CreateIndex(index).compile(dialect=dialect)))

        new_cols = [c.name for c in table.columns if c.name != "exam_id"]
        copy = [c for c in new_cols if c in cols]
        col_list = ", ".join(_ident(c) for c in copy)
        cur.execute(f"INSERT INTO submissions ({col_list}) SELECT {col_list} FROM submissions_old")  # nosemgrep

        copied_count = cur.execute("SELECT count(*) FROM submissions").fetchone()[0]
        if copied_count != before_count:
            raise RuntimeError(f"conteo distinto tras copiar: {before_count} -> {copied_count}")

        data_cols = [c for c in copy if c != "id"]
        data_list = ", ".join(_ident(c) for c in data_cols)
        assigned = unassigned = duplicated = 0
        for sub_id, student_id, problem_id in cur.execute(
            "SELECT id, student_id, problem_id FROM submissions"
        ).fetchall():
            exam_ids = _exams_for(cur, student_id, problem_id)
            if not exam_ids:
                unassigned += 1
                continue
            cur.execute("UPDATE submissions SET exam_id = ? WHERE id = ?", (exam_ids[0], sub_id))
            assigned += 1
            for extra in exam_ids[1:]:
                cur.execute(
                    f"INSERT INTO submissions ({data_list}, exam_id) "  # nosemgrep
                    f"SELECT {data_list}, ? FROM submissions WHERE id = ?",
                    (extra, sub_id),
                )
                duplicated += 1
        cur.execute("DROP TABLE submissions_old")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(
        f"[{db_path}] submissions reconstruida por examen: {before_count} filas, "
        f"{assigned} asignadas a un examen, {duplicated} copias para exámenes que compartían "
        f"la respuesta, {unassigned} sin intento (exam_id NULL)."
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m app.migrate_submissions_per_exam <ruta_a_la_bd.db>")
        sys.exit(1)
    migrate(sys.argv[1])
