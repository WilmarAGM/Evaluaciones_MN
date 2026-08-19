"""Backfill: agrega texto explicativo ('feedback') a checks_report de las
entregas ya calificadas de "Parcial Práctico Dos - Sesión 1/2" (exam_id 2 y 3).

No recalifica: verifica que total_score no cambie y salta (sin tocar esa fila)
si detecta una discrepancia. Solo enriquece cada item de checks_report con una
explicación en español de por qué pasó o falló, usando executor.explain_check.

Uso: python -m app.backfill_feedback_sesiones <ruta_a_la_bd.db>
"""
import json
import sqlite3
import sys

from . import executor

SESSION_EXAM_IDS = (2, 3)


def backfill(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    upd = conn.cursor()

    problems = cur.execute(
        """
        select p.id, p.rubric
        from exam_problems ep join problems p on p.id = ep.problem_id
        where ep.exam_id in (?, ?)
        """,
        SESSION_EXAM_IDS,
    ).fetchall()

    updated = 0
    skipped_mismatch = 0

    for prow in problems:
        problem_id = prow["id"]
        checks_cfg = json.loads(prow["rubric"])

        class _P:
            pass

        p = _P()
        p.rubric = prow["rubric"]

        subs = list(
            upd.execute(
                "select id, student_id, code, total_score from submissions where problem_id = ?",
                (problem_id,),
            )
        )
        for sub in subs:
            result = executor.run_student_code(sub["code"], checks_cfg)
            fresh = executor.grade_submission(result, p)

            if abs(fresh["total_score"] - sub["total_score"]) > 1e-6:
                skipped_mismatch += 1
                print(
                    f"SKIP (mismatch de score) problem={problem_id} student={sub['student_id']}: "
                    f"guardado={sub['total_score']} recalculado={fresh['total_score']}"
                )
                continue

            report = []
            for c, item in zip(checks_cfg, fresh["checks_report"]):
                entry = result["checks"].get(c["id"], {})
                feedback = executor.explain_check(c, entry, item["passed"])
                report.append({**item, "feedback": feedback})

            conn.execute(
                "update submissions set checks_report = ? where id = ?",
                (json.dumps(report), sub["id"]),
            )
            updated += 1

    conn.commit()
    conn.close()
    print(f"Entregas actualizadas: {updated}, saltadas por discrepancia: {skipped_mismatch}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m app.backfill_feedback_sesiones <ruta_a_la_bd.db>")
        sys.exit(1)
    backfill(sys.argv[1])
