"""Migración idempotente y de una sola vez: corrige exams.duration_minutes
de 50 a NULL para el examen 'Simulacro Parcial Final'.

Causa raíz (encontrada el 2026-09-23, ver models.py): la columna
duration_minutes tenía default=50 en SQLAlchemy, y ese default se aplicaba
también cuando el código pasaba duration_minutes=None EXPLÍCITAMENTE (no
solo cuando el atributo nunca se tocaba). seed_taller.py siempre construyó
este examen con duration_minutes=None ("sin límite de tiempo: el estudiante
puede entrar y salir libremente"), pero por ese bug quedó guardado con 50 —
el Simulacro ha corrido como examen de 50 minutos desde que se creó, nunca
como práctica libre sin límite.

Alcance DELIBERADAMENTE angosto: solo toca el examen con título exacto
'Simulacro Parcial Final' y duration_minutes=50, porque es el único caso
donde la intención original (sin límite) está documentada en el código que
lo crea. Otros exámenes con duration_minutes=50 (p.ej. 'Parcial Práctico
Dos', o exámenes de prueba creados a mano por el docente) si de verdad
querían un límite de tiempo, y no se tocan aquí.

Uso: python -m app.migrate_fix_untimed_exams <ruta_a_la_bd.db>
"""
import sqlite3
import sys

TARGET_TITLE = "Simulacro Parcial Final"


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cols = [row[1] for row in cur.execute("PRAGMA table_info(exams)")]
    if "duration_minutes" not in cols:
        print(f"[{db_path}] Tabla exams no tiene duration_minutes; nada que migrar.")
        conn.close()
        return

    row = cur.execute(
        "SELECT id, duration_minutes FROM exams WHERE title = ?", (TARGET_TITLE,)
    ).fetchone()
    if row is None:
        print(f"[{db_path}] No existe un examen titulado {TARGET_TITLE!r}; nada que migrar.")
    elif row[1] is None:
        print(f"[{db_path}] El examen {TARGET_TITLE!r} (id={row[0]}) ya tiene duration_minutes=NULL.")
    else:
        cur.execute("UPDATE exams SET duration_minutes = NULL WHERE id = ?", (row[0],))
        conn.commit()
        print(
            f"[{db_path}] Examen {TARGET_TITLE!r} (id={row[0]}): duration_minutes corregido "
            f"de {row[1]} a NULL (sin límite de tiempo, como estaba previsto)."
        )

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m app.migrate_fix_untimed_exams <ruta_a_la_bd.db>")
        sys.exit(1)
    migrate(sys.argv[1])
