"""Carga problemas a un banco a partir de un .tex, con un pipeline de 4
agentes (Gemini vía Google AI Studio):
  1) adapta los enunciados del .tex a problemas de programación viables SIN
     nombrar el método/algoritmo esperado (el estudiante debe decidirlo),
  2) genera una solución de referencia con numpy/scipy/sklearn,
  3) propone la rúbrica y la VALIDA ejecutándola de verdad contra la
     solución (ver gemini_agents.build_and_validate_rubric) — evalúa tanto el
     resultado final como el PROCEDIMIENTO (definir la función correcta,
     usar la rutina numérica correcta),
  4) audita el resultado: compara el valor calculado contra la respuesta de
     referencia del .tex original (si la trae) y revisa fidelidad/claridad
     del enunciado adaptado. Nunca bloquea la creación; deja una nota para
     que el docente la lea al revisar el borrador.

Los problemas se guardan con status="draft": no aparecen como opción al
armar un examen hasta que el docente los publique desde el dashboard
(Bancos de problemas -> "Publicar").

Uso: python -m app.load_problems_from_tex <archivo.tex> <bank_id> [--max N]
"""
import argparse
import sys

from .database import SessionLocal
from .gemini_agents import orchestrate_load_tex
from .gemini_quota import QuotaExceededError, get_usage_today


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tex_path", help="Ruta al archivo .tex con los enunciados")
    parser.add_argument("bank_id", type=int, help="ID del banco de problemas donde guardar")
    parser.add_argument("--max", type=int, default=None, help="Máximo de problemas a extraer del .tex")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = orchestrate_load_tex(args.tex_path, args.bank_id, db, max_problems=args.max)
    except QuotaExceededError as e:
        print(f"\nCupo diario propio de Gemini agotado: {e}. Intenta mañana o sube el límite en backend/.env.")
        sys.exit(1)
    finally:
        db.close()

    print(f"\nCreados {len(result['created'])} problema(s) como BORRADOR en el banco {result['bank_id']}:")
    for p in result["created"]:
        print(f"  - [{p['id']}] {p['title']} ({p['max_score']:.0f} pts)")
        if p.get("review_notes"):
            for line in p["review_notes"].splitlines():
                print(f"      {line}")

    if result["skipped"]:
        print(f"\nOmitidos {len(result['skipped'])} problema(s) (no se pudieron validar tras reintentos):")
        for s in result["skipped"]:
            print(f"  - {s['title']}: {s['reason']}")

    usage = get_usage_today()
    print(f"\nUso de Gemini hoy: {usage['calls']} llamado(s), {usage['tokens']} token(s).")
    print("Revisa y publica los borradores desde el dashboard (Bancos de problemas) antes de usarlos en un examen.")


if __name__ == "__main__":
    main()
