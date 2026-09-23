import json
import math
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

RUN_TIMEOUT_SECONDS = 20
RESULT_MARKER = "__EVAL_RESULT__"

# En producción (Docker) esto apunta al contenedor ejecutor aislado —sin la
# base de datos montada, sin .env, sin red a Internet— y el código del
# estudiante corre AHÍ, no en este proceso. Sin esta variable (dev local con
# `venv`, sin el contenedor ejecutor levantado) se cae al subproceso local de
# siempre, dejando claro en el docstring de run_student_code que ese modo no
# aísla nada y no debe usarse con estudiantes reales.
EXECUTOR_SERVICE_URL = os.environ.get("EXECUTOR_SERVICE_URL")

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


def __make_blocker(__qualname, __message):
    def __blocker(*args, **kwargs):
        raise RuntimeError(__message)
    return __blocker


# Deshabilita __qualname en este problema: cualquier llamada lanza un
# RuntimeError con __message en vez de ejecutarse. NO se usa un docstring
# aquí (comillas triples): este código vive dentro del propio string HELPERS,
# delimitado con comillas triples, y unas comillas triples anidadas lo
# cerrarían antes de tiempo.
def __block(__qualname, __message):
    __parts = __qualname.split(".")
    __module_path, __func_name = ".".join(__parts[:-1]), __parts[-1]
    try:
        __module = __importlib.import_module(__module_path)
    except Exception:
        return
    setattr(__module, __func_name, __make_blocker(__qualname, __message))
    __INSTRUMENTED_NAMES__.add(__func_name)


def __get_arg(args, kwargs, position, name):
    if position is not None and position < len(args):
        return True, args[position]
    if name is not None and name in kwargs:
        return True, kwargs[name]
    return False, None


def __isclose(a, b, tol=1e-6):
    try:
        if isinstance(a, str) or isinstance(b, str):
            # Comparación exacta: sirve para kwargs de texto de la propia
            # rutina de scipy (p.ej. method="iteration" en fixed_point), no
            # para "cuán parecidos" son dos textos. Antes de este chequeo,
            # una cadena caía en la rama de abajo (tiene __len__) y se
            # comparaba caracter por caracter con float(), lo que siempre
            # fallaba: un kwarg de texto nunca podía coincidir con nada.
            return a == b
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
            # str se deja tal cual (p.ej. method="iteration"); cualquier otra
            # cosa se intenta convertir a float para el detalle numérico.
            lines.append(
                f"    __got_{cid}_{i} = (__val_{cid}_{i} if isinstance(__val_{cid}_{i}, str) "
                f"else float(__val_{cid}_{i})) if __found_{cid}_{i} else None"
            )
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

    # blocked_call: rutinas deshabilitadas para ESTE problema porque
    # resolverían el ejercicio sin pasar por el método que se está evaluando
    # (ver __block). No es un check puntuado — no aparece en __RESULTS__ ni
    # en la rúbrica visible; si el estudiante la llama, su script revienta
    # ahí y las variables que dependían de esa llamada quedan sin definir.
    for c in checks:
        if c["type"] != "blocked_call":
            continue
        custom_message = c.get("message")
        for qn in c["qualnames"]:
            # Mensaje por rutina (nombra la que el estudiante realmente llamó),
            # salvo que la rúbrica traiga un texto propio para todo el grupo.
            message = custom_message or f"{qn} no está permitido en este problema; usa el método que pide el enunciado."
            lines.append(f"__block({qn!r}, {message!r})")
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
    # matplotlib se importa UNA vez aquí (no en cada check "plot" ni de nuevo
    # más abajo al capturar las figuras): "Agg" porque este proceso no tiene
    # pantalla, así que plt.show()/plt.plot() no pueden fallar ni bloquear
    # esperando una ventana.
    lines.append("try:")
    lines.append("    import matplotlib as __mpl")
    lines.append("    __mpl.use('Agg')")
    lines.append("    import matplotlib.pyplot as __plt")
    lines.append("    __FIGURE_COUNT__ = len(__plt.get_fignums())")
    lines.append("except Exception:")
    lines.append("    __plt = None")
    lines.append("    __FIGURE_COUNT__ = 0")
    lines.append("")

    for c in checks:
        if c["type"] == "blocked_call":
            continue  # sin id, sin resultado: ver __block en el preámbulo
        if c["type"] == "plot":
            # Solo comprueba que el estudiante dejó al menos min_figures
            # gráficas abiertas — no compara contra una referencia (verificar
            # que la CURVA sea la correcta es mucho más frágil: distintas
            # formas legítimas de graficar la misma f dan objetos Line2D muy
            # distintos). La gráfica en sí SIEMPRE se le muestra al
            # estudiante (ver figuras más abajo), sea o no la esperada.
            lines.append(
                f"__RESULTS__[{c['id']!r}] = {{'passed': __FIGURE_COUNT__ >= {c.get('min_figures', 1)!r}}}"
            )
            continue
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
            # __module__ == '__main__' cubre una función 'def'-inida por el
            # estudiante; None cubre una función compilada dinámicamente sin
            # módulo propio, como sp.lambdify(...) (patrón legítimo: definir
            # f simbólicamente con sympy y convertirla a numérica para
            # pasarla a scipy). Cualquier función importada de verdad —
            # incluida la de referencia, si alguien intentara acceder a
            # ella— tiene su módulo real (p.ej. 'scipy.optimize', 'trapecio'),
            # nunca '__main__' ni None, así que ese atajo sigue bloqueado.
            lines.append("        if getattr(__val, '__module__', None) not in ('__main__', None):")
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
            # .item() sirve para un escalar numpy (0-d o tamaño 1); un vector o
            # matriz (p.ej. la matriz de iteración de Jacobi/Gauss-Seidel/SOR,
            # o la solución de un sistema con scipy.linalg.solve) lanza
            # ValueError ahí, así que se cae a .tolist() para conservarlo como
            # lista (anidada si es 2D) serializable en JSON.
            lines.append("    if hasattr(__v, 'item'):")
            lines.append("        try:")
            lines.append("            __v = __v.item()")
            lines.append("        except (ValueError, TypeError):")
            lines.append("            __v = __v.tolist() if hasattr(__v, 'tolist') else __v")
            lines.append(f"    __RESULTS__[{cid!r}] = {{'value': __v}}")
            lines.append("except KeyError:")
            lines.append(
                f"    __RESULTS__[{cid!r}] = {{'error': \"La variable '{var}' no fue definida\"}}"
            )
            lines.append("except Exception as __e:")
            lines.append(f"    __RESULTS__[{cid!r}] = {{'error': str(__e)}}")
            lines.append("")

    # Captura de gráficas: cualquier figura que el código del estudiante haya
    # dejado abierta (contada arriba en __FIGURE_COUNT__, para el check
    # "plot") se codifica como PNG en base64 para que el frontend la muestre
    # (ver ProblemCard.jsx). Reutiliza el __plt ya importado más arriba.
    lines.append("__FIGURES__ = []")
    lines.append("if __plt is not None:")
    lines.append("    try:")
    lines.append("        import io as __io, base64 as __base64")
    lines.append("        for __fignum in __plt.get_fignums():")
    lines.append("            __fig = __plt.figure(__fignum)")
    lines.append("            __buf = __io.BytesIO()")
    lines.append("            __fig.savefig(__buf, format='png', dpi=100, bbox_inches='tight')")
    lines.append("            __FIGURES__.append(__base64.b64encode(__buf.getvalue()).decode('ascii'))")
    lines.append("        __plt.close('all')")
    lines.append("    except Exception:")
    lines.append("        pass")
    lines.append("")

    lines.append(f'print("{RESULT_MARKER}" + _json.dumps({{"checks": __RESULTS__, "figures": __FIGURES__}}))')
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


def _run_in_sandbox_service(full_script: str) -> tuple[str, str]:
    """Envía el script ya ensamblado al contenedor ejecutor aislado (ver
    executor_service/server.py) y devuelve (stdout, stderr). El script corre
    ALLÁ, en un contenedor sin la base de datos montada, sin .env y sin red
    a Internet — nunca en este proceso."""
    body = json.dumps({"script": full_script, "timeout": RUN_TIMEOUT_SECONDS}).encode("utf-8")
    req = urllib.request.Request(
        f"{EXECUTOR_SERVICE_URL}/run", data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=RUN_TIMEOUT_SECONDS + 10) as resp:
            payload = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, OSError):
        return "", "El entorno de ejecución no respondió. Intenta de nuevo en unos segundos."
    return payload.get("stdout", ""), payload.get("stderr", "")


def _run_locally(full_script: str) -> tuple[str, str]:
    """Respaldo SOLO para desarrollo local sin Docker (p.ej. corriendo con
    `venv` directamente, como en las auditorías de este executor). No aísla
    filesystem/red/base de datos: el código del estudiante corre en este
    mismo proceso Python con este mismo usuario. NUNCA se activa si
    EXECUTOR_SERVICE_URL está definida, que es como se despliega siempre en
    Docker (ver docker-entrypoint.sh / docker-executor-setup.sh)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        proc = subprocess.run(
            [sys.executable, "-"],
            input=full_script,
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )
        return proc.stdout, proc.stderr


def run_student_code(code: str, checks: list) -> dict:
    """Ejecuta el código del estudiante, instrumentado según la lista `checks`
    (rúbrica del problema) para poder verificar imports/llamadas/funciones
    definidas y variables finales.

    El script se arma aquí (conoce la rúbrica) pero se EJECUTA en el
    contenedor ejecutor aislado vía EXECUTOR_SERVICE_URL (ver
    _run_in_sandbox_service): sin la base de datos, sin secretos, sin red a
    Internet, con límites de CPU/memoria/procesos propios además de los del
    contenedor. Sin esa variable de entorno (solo en desarrollo local sin
    Docker) se cae a _run_locally, que NO aísla nada — ver su docstring."""
    full_script = _build_runner(code, checks)

    try:
        if EXECUTOR_SERVICE_URL:
            stdout, stderr = _run_in_sandbox_service(full_script)
        else:
            stdout, stderr = _run_locally(full_script)
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Tiempo de ejecución excedido ({RUN_TIMEOUT_SECONDS}s).",
            "checks": {},
            "figures": [],
        }

    payload = {}
    visible_stdout_lines = []
    for line in stdout.splitlines():
        if line.startswith(RESULT_MARKER):
            payload = json.loads(line[len(RESULT_MARKER):])
        else:
            visible_stdout_lines.append(line)

    return {
        "stdout": "\n".join(visible_stdout_lines),
        "stderr": stderr,
        "checks": payload.get("checks", {}),
        "figures": payload.get("figures", []),
    }


def _values_close(value, expected, tol) -> bool:
    """Como math.isclose, pero también acepta vectores/matrices (listas
    anidadas) para poder calificar una respuesta final como scipy.linalg.solve
    o una matriz de iteración de Jacobi/Gauss-Seidel/SOR, no solo un escalar.
    (El lado del ejecutor ya deja los numpy arrays como listas vía
    .tolist() — ver _build_footer — así que aquí solo llegan tipos JSON.)"""
    if isinstance(expected, (list, tuple)) or isinstance(value, (list, tuple)):
        if not isinstance(value, (list, tuple)) or not isinstance(expected, (list, tuple)):
            return False
        if len(value) != len(expected):
            return False
        return all(_values_close(v, e, tol) for v, e in zip(value, expected))
    try:
        return math.isclose(value, expected, abs_tol=tol)
    except TypeError:
        return False


def grade_submission(run_result: dict, problem) -> dict:
    checks_cfg = json.loads(problem.rubric)
    results = run_result.get("checks", {})

    report = []
    total = 0.0
    for c in checks_cfg:
        if c["type"] == "blocked_call":
            continue  # no es un criterio puntuado; ver __block en executor.py
        cid = c["id"]
        max_points = c["points"]
        entry = results.get(cid, {}) or {}

        if c["type"] == "final_value":
            value = entry.get("value")
            passed = False
            if value is not None and "error" not in entry:
                passed = _values_close(value, c["expected"], c.get("tolerance", 1e-4))
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
        if isinstance(expected, (list, tuple)) or isinstance(value, (list, tuple)):
            # Vector o matriz (p.ej. la solución de un sistema o una matriz de
            # iteración): no hay un "diff" único que reportar, se muestran
            # ambos valores completos.
            if passed:
                return f"'{var}' = {value!r}, coincide con lo esperado."
            return f"'{var}' = {value!r}, pero se esperaba {expected!r} (tolerancia {tol:.2g} por componente)."
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
                got, expected = d.get("got"), d["expected"]
                got_str = f"{got:g}" if isinstance(got, (int, float)) else (repr(got) if got is not None else "no se pudo leer")
                expected_str = f"{expected:g}" if isinstance(expected, (int, float)) else repr(expected)
                parts.append(f"'{d['name']}' = {got_str} (se esperaba {expected_str})")
        return "Llamaste a la rutina, pero " + "; ".join(parts) + "."

    if ctype == "plot":
        return "Generaste al menos una gráfica." if passed else "No generaste ninguna gráfica."

    return ""
