import json
import math
import os
import subprocess
import sys
import tempfile

RUN_TIMEOUT_SECONDS = 20
RESULT_MARKER = "__EVAL_RESULT__"

# Carpeta con las rutinas propias del curso (Euler.py, RK4_sist.py, Poisson.py, ...)
# Se agrega al sys.path del subproceso para que el estudiante pueda hacer
# "from RK4_sist import RK4_sist", igual que en las rutinas del profesor.
RUTINAS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "Rutinas_MN_Python_Est")
)

HELPERS = """
import sys as __sys
__sys.path.insert(0, {rutinas_dir!r})

import importlib as __importlib
import inspect as __inspect
import math as __math
import numpy as np

__CALL_LOG__ = []
__INSTRUMENTED_NAMES__ = set()


def __make_wrapper(__qualname, __original):
    def __wrapper(*args, **kwargs):
        __CALL_LOG__.append((__qualname, list(args), dict(kwargs)))
        return __original(*args, **kwargs)
    return __wrapper


def __patch(__qualname):
    __parts = __qualname.split(".")
    __module_path, __func_name = ".".join(__parts[:-1]), __parts[-1]
    try:
        __module = __importlib.import_module(__module_path)
        __original = getattr(__module, __func_name)
    except Exception:
        return
    setattr(__module, __func_name, __make_wrapper(__qualname, __original))
    __INSTRUMENTED_NAMES__.add(__func_name)


def __get_arg(args, kwargs, position, name):
    if position is not None and position < len(args):
        return True, args[position]
    if name is not None and name in kwargs:
        return True, kwargs[name]
    return False, None


def __isclose(a, b, tol=1e-6):
    try:
        if hasattr(a, "__len__") or hasattr(b, "__len__"):
            a, b = list(a), list(b)
            return len(a) == len(b) and all(__isclose(x, y, tol) for x, y in zip(a, b))
        return __math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)
    except Exception:
        return False


def __matches_ref(fn, ref, points, tol=1e-6):
    if ref is None or not points:
        return False
    try:
        for p in points:
            if not __isclose(fn(*p), ref(*p), tol):
                return False
        return True
    except Exception:
        return False
"""


def _condition_expr(match: dict) -> str:
    pos = match.get("position")
    name = match.get("name")
    base = f"__get_arg(__a, __k, {pos!r}, {name!r})"
    if "ref" in match:
        ref_id = match["ref"]
        return (
            f"({base}[0] and callable({base}[1]) and "
            f"__matches_ref({base}[1], __ref_{ref_id}, __points_{ref_id}))"
        )
    expected = match["expected"]
    tol = match.get("tol", 1e-6)
    return f"({base}[0] and __isclose({base}[1], {expected!r}, {tol!r}))"


def _arg_detail_lines(cid: str, match_args: list) -> list[str]:
    """Genera líneas que, dado el PRIMER intento de llamada a la rutina
    (__a0/__k0), arman un detalle por argumento (esperado vs. obtenido) para
    poder explicarle al estudiante qué argumento no coincide. Solo se usa
    para construir feedback explicativo, nunca para decidir passed/failed."""
    lines = [f"__detail_{cid} = []"]
    for i, m in enumerate(match_args):
        pos = m.get("position")
        name = m.get("name")
        label = name or f"arg{pos}"
        base = f"__get_arg(__a0, __k0, {pos!r}, {name!r})"
        if "ref" in m:
            ref_id = m["ref"]
            lines.append(f"__found_{cid}_{i}, __val_{cid}_{i} = {base}")
            lines.append(
                f"__ok_{cid}_{i} = bool(__found_{cid}_{i} and callable(__val_{cid}_{i}) and "
                f"__matches_ref(__val_{cid}_{i}, __ref_{ref_id}, __points_{ref_id}))"
            )
            lines.append(
                f"__detail_{cid}.append({{'name': {label!r}, 'kind': 'function', 'ok': __ok_{cid}_{i}}})"
            )
        else:
            expected = m["expected"]
            tol = m.get("tol", 1e-6)
            lines.append(f"__found_{cid}_{i}, __val_{cid}_{i} = {base}")
            lines.append(
                f"__ok_{cid}_{i} = bool(__found_{cid}_{i} and __isclose(__val_{cid}_{i}, {expected!r}, {tol!r}))"
            )
            lines.append("try:")
            lines.append(f"    __got_{cid}_{i} = float(__val_{cid}_{i}) if __found_{cid}_{i} else None")
            lines.append("except Exception:")
            lines.append(f"    __got_{cid}_{i} = None")
            lines.append(
                f"__detail_{cid}.append({{'name': {label!r}, 'kind': 'value', "
                f"'expected': {expected!r}, 'got': __got_{cid}_{i}, 'ok': __ok_{cid}_{i}}})"
            )
    return lines


def _build_preamble(checks: list) -> str:
    # OJO: las funciones de referencia (__ref_X) NO se definen aquí, sino en el
    # footer (después de ejecutar el código del estudiante). Así, mientras el
    # código del estudiante corre, esas funciones todavía no existen en el
    # namespace del proceso — ni siquiera son alcanzables vía
    # sys.modules["__main__"] — y no se pueden usar como atajo para "resolver"
    # el problema.
    lines = [HELPERS.format(rutinas_dir=RUTINAS_DIR), ""]

    qualnames = sorted({qn for c in checks if c["type"] == "call" for qn in c["qualnames"]})
    for qn in qualnames:
        lines.append(f"__patch({qn!r})")
    lines.append("")

    return "\n".join(lines)


def _build_footer(checks: list) -> str:
    lines = ["import json as _json", ""]

    for c in checks:
        if c["type"] != "function":
            continue
        arg_names = ", ".join(c["arg_names"])
        lines.append(f"def __ref_{c['id']}({arg_names}):")
        lines.append(f"    return ({c['ref_body']})")
        lines.append("")

    lines.append("__skip = set(__INSTRUMENTED_NAMES__)")
    lines.append("__RESULTS__ = {}")
    lines.append("")

    for c in checks:
        cid = c["id"]
        if c["type"] == "function":
            n_args = len(c["arg_names"])
            lines.append(f"__points_{cid} = {c.get('test_points', [])!r}")
            lines.append(f"__found_{cid} = False")
            lines.append(f"__cand_{cid} = None")
            lines.append("try:")
            lines.append("    for __name, __val in list(__STUDENT_NS.items()):")
            lines.append("        if __name.startswith('__') or __name in __skip:")
            lines.append("            continue")
            lines.append("        if not callable(__val):")
            lines.append("            continue")
            lines.append("        if getattr(__val, '__module__', None) != '__main__':")
            lines.append("            continue")
            lines.append(f"        if __matches_ref(__val, __ref_{cid}, __points_{cid}):")
            lines.append(f"            __found_{cid} = True")
            lines.append(f"            __cand_{cid} = __val")
            lines.append("            break")
            lines.append(f"        elif __cand_{cid} is None:")
            lines.append("            try:")
            lines.append(f"                if len(__inspect.signature(__val).parameters) == {n_args}:")
            lines.append(f"                    __cand_{cid} = __val")
            lines.append("            except Exception:")
            lines.append("                pass")
            lines.append("except Exception:")
            lines.append("    pass")
            # __cand_{cid}, cuando no hubo match exacto, es solo la mejor
            # candidata plausible (misma aridad) para poder mostrarle al
            # estudiante un ejemplo concreto de en qué difiere — nunca se usa
            # para decidir passed/failed.
            lines.append(f"__samples_{cid} = []")
            lines.append(f"if not __found_{cid} and __cand_{cid} is not None:")
            lines.append(f"    for __p in __points_{cid}[:3]:")
            lines.append("        try:")
            lines.append(f"            __got = __cand_{cid}(*__p)")
            lines.append("            if hasattr(__got, 'item'):")
            lines.append("                __got = __got.item()")
            lines.append("            __got = float(__got)")
            lines.append("            __err = None")
            lines.append("        except Exception as __e:")
            lines.append("            __got = None")
            lines.append("            __err = str(__e)")
            lines.append("        try:")
            lines.append(f"            __exp = float(__ref_{cid}(*__p))")
            lines.append("        except Exception:")
            lines.append("            __exp = None")
            lines.append(
                f"        __samples_{cid}.append({{'args': list(__p), 'expected': __exp, "
                "'got': __got, 'error': __err})"
            )
            lines.append(f"__RESULTS__[{cid!r}] = {{'passed': __found_{cid}, 'samples': __samples_{cid}}}")
            lines.append("")

        elif c["type"] == "call":
            lines.append(f"__qns_{cid} = {c['qualnames']!r}")
            lines.append(
                f"__matched_{cid} = [t for t in __CALL_LOG__ if t[0] in __qns_{cid}]"
            )
            if c.get("strict"):
                lines.append(f"__ok_{cid} = False")
                lines.append(f"__q0_{cid} = __a0_{cid} = __k0_{cid} = None")
                lines.append("try:")
                lines.append(f"    for __q, __a, __k in __matched_{cid}:")
                conds = [_condition_expr(m) for m in c.get("match_args", [])]
                cond_expr = " and ".join(conds) if conds else "True"
                lines.append(f"        if {cond_expr}:")
                lines.append(f"            __ok_{cid} = True")
                lines.append("            break")
                lines.append("except Exception:")
                lines.append("    pass")
                lines.append(f"__detail_{cid} = []")
                lines.append(f"if not __ok_{cid} and __matched_{cid}:")
                lines.append(f"    __q0, __a0, __k0 = __matched_{cid}[0]")
                lines.append("    try:")
                for l in _arg_detail_lines(cid, c.get("match_args", [])):
                    lines.append("        " + l)
                lines.append("    except Exception:")
                lines.append("        pass")
                lines.append(
                    f"__RESULTS__[{cid!r}] = {{'passed': __ok_{cid}, "
                    f"'called': len(__matched_{cid}) > 0, 'arg_detail': __detail_{cid}}}"
                )
            else:
                lines.append(
                    f"__RESULTS__[{cid!r}] = {{'passed': len(__matched_{cid}) > 0, "
                    f"'called': len(__matched_{cid}) > 0}}"
                )
            lines.append("")

        elif c["type"] == "final_value":
            var = c["variable"]
            lines.append("try:")
            lines.append(f"    __v = __STUDENT_NS[{var!r}]")
            lines.append("    if hasattr(__v, 'item'):")
            lines.append("        __v = __v.item()")
            lines.append(f"    __RESULTS__[{cid!r}] = {{'value': __v}}")
            lines.append("except KeyError:")
            lines.append(
                f"    __RESULTS__[{cid!r}] = {{'error': \"La variable '{var}' no fue definida\"}}"
            )
            lines.append("except Exception as __e:")
            lines.append(f"    __RESULTS__[{cid!r}] = {{'error': str(__e)}}")
            lines.append("")

    lines.append(f'print("{RESULT_MARKER}" + _json.dumps(__RESULTS__))')
    return "\n".join(lines)


def _build_runner(code: str, checks: list) -> str:
    """Ensambla el script completo. El código del estudiante se ejecuta en un
    namespace propio (__STUDENT_NS), separado del namespace donde viven las
    funciones de referencia y el registro de llamadas: así el estudiante no
    puede acceder a esos internos (p.ej. haciendo f = __ref_def_f) ni leerlos
    inspeccionando globals()."""
    preamble = _build_preamble(checks)
    footer = _build_footer(checks)

    lines = [preamble, ""]
    lines.append(f"__STUDENT_SRC = {code!r}")
    lines.append('__STUDENT_NS = {"__name__": "__main__"}')
    lines.append("try:")
    lines.append('    exec(compile(__STUDENT_SRC, "celda_de_codigo.py", "exec"), __STUDENT_NS)')
    lines.append("except Exception:")
    lines.append("    import traceback as __traceback")
    lines.append("    __traceback.print_exc()")
    lines.append("")
    lines.append(footer)
    return "\n".join(lines)


def run_student_code(code: str, checks: list) -> dict:
    """Ejecuta el código del estudiante en un subproceso aislado con timeout,
    instrumentado según la lista `checks` (rúbrica del problema) para poder
    verificar imports/llamadas/funciones definidas y variables finales.

    El script se pasa por stdin (no se escribe a disco) y el código del
    estudiante corre en su propio namespace, para que no pueda leer el script
    ni acceder directamente a las funciones/datos de referencia usados para
    calificar.

    NOTA: este executor es solo para el prototipo LOCAL de prueba. No aisla
    filesystem/red como haría un contenedor Docker; no usar tal cual en producción
    con estudiantes no confiables.
    """
    full_script = _build_runner(code, checks)

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            proc = subprocess.run(
                [sys.executable, "-"],
                input=full_script,
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=RUN_TIMEOUT_SECONDS,
            )
            stdout, stderr = proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Tiempo de ejecución excedido ({RUN_TIMEOUT_SECONDS}s).",
                "checks": {},
            }

    results = {}
    visible_stdout_lines = []
    for line in stdout.splitlines():
        if line.startswith(RESULT_MARKER):
            results = json.loads(line[len(RESULT_MARKER):])
        else:
            visible_stdout_lines.append(line)

    return {"stdout": "\n".join(visible_stdout_lines), "stderr": stderr, "checks": results}


def grade_submission(run_result: dict, problem) -> dict:
    checks_cfg = json.loads(problem.rubric)
    results = run_result.get("checks", {})

    report = []
    total = 0.0
    for c in checks_cfg:
        cid = c["id"]
        max_points = c["points"]
        entry = results.get(cid, {}) or {}

        if c["type"] == "final_value":
            value = entry.get("value")
            passed = False
            if value is not None and "error" not in entry:
                try:
                    passed = math.isclose(value, c["expected"], abs_tol=c.get("tolerance", 1e-4))
                except TypeError:
                    passed = False
        else:
            # "function"/"call" ahora llegan como dicts ({'passed': ..., ...detalle})
            # para poder explicar el porqué; el bool a secas se sigue aceptando
            # por compatibilidad con resultados antiguos.
            passed = bool(entry.get("passed", False)) if isinstance(entry, dict) else bool(entry)

        points = max_points if passed else 0.0
        total += points
        report.append({"label": c["label"], "passed": passed, "points": points, "max_points": max_points})

    return {"total_score": total, "checks_report": report}


def explain_check(c: dict, entry, passed: bool) -> str:
    """Traduce el detalle crudo de un check (valor/función/llamada) a una
    explicación breve en español de por qué pasó o falló. Pensado para
    revisiones posteriores al examen (no se usa en la calificación en vivo,
    para no revelar valores esperados durante un intento en curso)."""
    ctype = c["type"]
    entry = entry if isinstance(entry, dict) else {}

    if ctype == "final_value":
        var = c["variable"]
        if "error" in entry:
            return f"No se pudo leer '{var}': {entry['error']}."
        value = entry.get("value")
        if value is None:
            return f"La variable '{var}' no fue definida."
        expected = c["expected"]
        tol = c.get("tolerance", 1e-4)
        try:
            diff = abs(float(value) - expected)
        except (TypeError, ValueError):
            return f"'{var}' = {value!r} no es un número comparable con el valor esperado."
        if passed:
            return f"'{var}' = {value:.6g}, coincide con el valor esperado {expected:.6g} (diferencia {diff:.2g})."
        return (
            f"'{var}' = {value:.6g}, pero se esperaba {expected:.6g} "
            f"(diferencia {diff:.2g} supera la tolerancia {tol:.2g})."
        )

    if ctype == "function":
        if passed:
            return "Tu función coincide con la esperada en todos los puntos de prueba."
        samples = entry.get("samples") or []
        if not samples:
            return "No encontramos una función tuya que se pudiera comparar con lo pedido."
        parts = []
        for s in samples:
            args_str = ", ".join(f"{a:g}" if isinstance(a, (int, float)) else str(a) for a in s["args"])
            if s.get("error"):
                parts.append(f"en ({args_str}) tu función lanzó un error: {s['error']}")
            elif s.get("got") is None or s.get("expected") is None:
                parts.append(f"en ({args_str}) no se pudo comparar el resultado")
            else:
                parts.append(f"en ({args_str}) tu función da {s['got']:.4g} y se esperaba {s['expected']:.4g}")
        return "Tu función no coincide con la esperada: " + "; ".join(parts) + "."

    if ctype == "call":
        if not entry.get("called", False):
            qualnames = ", ".join(c["qualnames"])
            return f"No detectamos ninguna llamada a {qualnames}."
        if passed:
            return "Llamaste a la rutina correcta con los argumentos esperados."
        bad = [d for d in (entry.get("arg_detail") or []) if not d["ok"]]
        if not bad:
            return "Llamaste a la rutina, pero con argumentos distintos a los esperados."
        parts = []
        for d in bad:
            if d["kind"] == "function":
                parts.append(f"el argumento '{d['name']}' no es la función esperada")
            else:
                got = d.get("got")
                got_str = f"{got:g}" if isinstance(got, (int, float)) else "no se pudo leer"
                parts.append(f"'{d['name']}' = {got_str} (se esperaba {d['expected']:g})")
        return "Llamaste a la rutina, pero " + "; ".join(parts) + "."

    return ""
