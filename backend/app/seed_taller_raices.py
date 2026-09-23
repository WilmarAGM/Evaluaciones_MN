"""Banco de problemas 'Raíces y sistemas no lineales' a partir del taller de
métodos numéricos del docente (numerales 1.1-1.10 + sistemas lineales/
iterativos). Cubre SOLO las partes de cada numeral con un resultado numérico
verificable (raíz, número de iteraciones, matriz, etc.) — las partes de
"explique/compare/construya una tabla" no tienen chequeo automático y quedan
fuera a propósito (decisión del docente, 2026-09-22): se piden aparte.

Todos los valores 'expected' de las rúbricas se calcularon ejecutando la
misma rutina de scipy que se le exige al estudiante (ver
compute_reference_values), nunca a mano — un valor a mano ya causó un error
real en esta sesión (la matriz de iteración de Jacobi de la prueba de
álgebra lineal).

Se crean en status='draft': un docente debe revisarlos y publicarlos, igual
que el resto del pipeline de carga de problemas (ver gemini_agents.py).

Uso: python -m app.seed_taller_raices
"""
import json

import numpy as np
from scipy.optimize import bisect, fixed_point

from .database import SessionLocal, Base, engine
from . import models

BANK_TITLE = "Raíces y sistemas no lineales — Taller"
BANK_GROUP = 1  # ajustar si el docente dueño del taller es de otro grupo

METODOS_ALTERNOS_RAICES = [
    "scipy.optimize.brentq",
    "scipy.optimize.newton",
    "scipy.optimize.fsolve",
    "scipy.optimize.root_scalar",
    "scipy.optimize.ridder",
    "sympy.nsolve",
    "sympy.solve",
]


def compute_reference_values():
    """Calcula TODOS los valores de referencia ejecutando de verdad las
    mismas rutinas que se exigen al estudiante. Ver auditoría del 2026-09-22
    (backend/app/executor.py) para los scripts de scaneo usados originalmente."""
    v = {}

    # 1.1: f = cos(x) - sin(e^x), menor cero positivo
    f11 = lambda x: np.cos(x) - np.sin(np.exp(x))
    r, info = bisect(f11, 0.5, 1.0, xtol=1e-8, full_output=True)
    v["1.1"] = {"r": r, "iters": float(info.iterations), "calls": float(info.function_calls)}

    # 1.2: f = e^x - 3x^2, tres raíces reales
    f12 = lambda x: np.exp(x) - 3 * x**2
    v["1.2"] = {}
    for name, (a, b) in {"r1": (-1.0, 0.0), "r2": (0.0, 2.0), "r3": (3.0, 4.0)}.items():
        r, info = bisect(f12, a, b, xtol=1e-10, full_output=True)
        v["1.2"][name] = {"a": a, "b": b, "r": r, "iters": float(info.iterations)}

    # 1.3: f = ln|(1+x)/(1-x^2)| = ln|1/(1-x)|, ceros en x=0 y x=2
    def f13(x):
        with np.errstate(all="ignore"):
            return np.log(np.abs((1 + x) / (1 - x**2)))
    v["1.3"] = {}
    for name, (a, b) in {"r1": (-0.5, 0.5), "r2": (1.5, 2.5)}.items():
        r, info = bisect(f13, a, b, xtol=1e-9, full_output=True)
        v["1.3"][name] = {"a": a, "b": b, "r": r, "iters": float(info.iterations)}

    # 1.4: cos(e^x-2) = e^x/4 - 2, tres raíces en [0,3]
    f14 = lambda x: np.cos(np.exp(x) - 2) - (np.exp(x) / 4 - 2)
    v["1.4"] = {}
    for name, (a, b) in {"r1": (1.0, 1.8), "r2": (1.8, 1.9), "r3": (2.0, 2.5)}.items():
        r, info = bisect(f14, a, b, xtol=1e-9, full_output=True)
        v["1.4"][name] = {"a": a, "b": b, "r": r, "iters": float(info.iterations)}

    # 1.5: f = e^x cos(3x) - sin(5x+1) en [-2, 1.5]; f' analítica
    f15 = lambda x: np.exp(x) * np.cos(3 * x) - np.sin(5 * x + 1)
    a15, b15 = -2.0, 1.5
    crit_intervals = [(-1.9, -1.7), (-1.2, -1.0), (-0.5, -0.3), (0.05, 0.2), (0.4, 0.6), (1.15, 1.35)]
    crits = []
    for a, b in crit_intervals:
        fp15 = lambda x: np.exp(x) * (np.cos(3 * x) - 3 * np.sin(3 * x)) - 5 * np.cos(5 * x + 1)
        r, _ = bisect(fp15, a, b, xtol=1e-10, full_output=True)
        crits.append(r)
    candidatos = [(f15(x), x) for x in crits] + [(f15(a15), a15), (f15(b15), b15)]
    fmax, xmax = max(candidatos)
    fmin, xmin = min(candidatos)
    v["1.5"] = {"fmax": fmax, "xmax": xmax, "fmin": fmin, "xmin": xmin}

    # 1.6: puntos fijos de h y g, obtenidos con bisect sobre x-h(x)/x-g(x)
    # porque fixed_point(method='iteration') diverge cerca de ellos
    h = lambda x: 4 * np.sin(x) + np.exp(x) - 5
    g16 = lambda x: np.exp(x * np.cos(x)) - 10 * np.arctan(x**3 / (x**2 + 1))
    rh, _ = bisect(lambda x: x - h(x), 0.5, 1.5, xtol=1e-10, full_output=True)
    rg, _ = bisect(lambda x: x - g16(x), 0.0, 1.0, xtol=1e-10, full_output=True)
    v["1.6"] = {"rh": rh, "rg": rg}

    # 1.7: g(x)=x^(x-cos x); con method='del2' (por defecto) ambos x0 (1.2 y
    # 1.4) convergen al MISMO punto fijo (no trivial, distinto de x=1)
    def g17(x):
        with np.errstate(all="ignore"):
            return x ** (x - np.cos(x))
    r17 = float(fixed_point(g17, 1.4, xtol=1e-9, maxiter=100))
    v["1.7"] = {"r": r17}

    # 1.8: g(x)=2^-x en [1/3,1], p0=0.5, xtol=1e-6
    g18 = lambda x: 2.0 ** (-x)
    gp18 = lambda x: -np.log(2) * 2.0 ** (-x)
    k = max(abs(gp18(1 / 3)), abs(gp18(1)))
    p0 = 0.5
    n_pred = next(n for n in range(1, 500) if k**n / (1 - k) * abs(g18(p0) - p0) < 1e-6)
    punto_fijo = float(fixed_point(g18, p0, method="iteration", xtol=1e-6, maxiter=200))
    maxiter_min = next(
        m for m in range(1, 100)
        if _converges(lambda: fixed_point(g18, p0, method="iteration", xtol=1e-6, maxiter=m))
    )
    v["1.8"] = {"k": k, "n_pred": float(n_pred), "punto_fijo": punto_fijo, "maxiter_min": float(maxiter_min)}

    # 1.9: x^3+x^2-3x-3=0, raíz r=sqrt(3); g1 con x0=1.5 converge a OTRA raíz (-1)
    g1 = lambda x: (x**3 + x**2 - 3) / 3
    conv_g1 = float(fixed_point(g1, 1.5, method="iteration", xtol=1e-10, maxiter=200))
    v["1.9"] = {"raiz_sqrt3": float(np.sqrt(3)), "conv_g1_desde_1_5": conv_g1}

    # 1.10: tan(x)=x cerca de 4.5
    f110 = lambda x: x - np.tan(x)
    r110, info110 = bisect(f110, 4.4, 4.5, xtol=1e-12, full_output=True)
    g110 = lambda x: np.arctan(x) + np.pi
    r110b = float(fixed_point(g110, 4.5, method="iteration", xtol=1e-12, maxiter=500))
    v["1.10"] = {"r": r110, "iters": float(info110.iterations), "r_fixed_point": r110b}

    # Sistema lineal + matrices de iteración (Jacobi/Gauss-Seidel/SOR) —
    # ejemplo de sistema 3x3 diagonalmente dominante, para que las tres
    # iteraciones converjan.
    A = np.array([[10.0, -1.0, 2.0], [1.0, 11.0, -1.0], [2.0, -1.0, 10.0]])
    b = np.array([6.0, 25.0, -11.0])
    x_sol = np.linalg.solve(A, b)
    D = np.diag(np.diag(A))
    L = -np.tril(A, -1)
    U = -np.triu(A, 1)
    Dinv = np.linalg.inv(D)
    T_jacobi = Dinv @ (L + U)
    T_gs = np.linalg.inv(D - L) @ U
    omega = 1.1
    T_sor = np.linalg.inv(D - omega * L) @ ((1 - omega) * D + omega * U)
    v["sistemas"] = {
        "A": A.tolist(), "b": b.tolist(), "x": x_sol.tolist(),
        "T_jacobi": T_jacobi.tolist(), "T_gs": T_gs.tolist(), "T_sor": T_sor.tolist(), "omega": omega,
    }
    return v


def _converges(call):
    try:
        call()
        return True
    except Exception:
        return False


def build_problems(v: dict) -> list[dict]:
    """Cada dict: {title, statement_md, starter_code, rubric (list de checks)}."""
    problems = []

    # ---------------- 1.1 ----------------
    problems.append({
        "title": "1.1 — Menor cero positivo de f(x)=cos(x)-sin(e^x)",
        "statement_md": (
            "Sea $f(x)=\\cos(x)-\\sin(e^x)$.\n\n"
            "1. Grafique $f$ en $[0,3]$.\n"
            "2. Aproxime el **menor cero positivo** con `scipy.optimize.bisect` en el intervalo $[0.5, 1.0]$, "
            "usando `xtol=1e-8` y `full_output=True`. Guarde la raíz en `r`, el número de iteraciones en "
            "`iteraciones` y el número de llamadas a la función en `llamadas`."
        ),
        "starter_code": "import numpy as np\nimport matplotlib.pyplot as plt\nfrom scipy.optimize import bisect\n\n# f, gráfica, y luego bisect(...)\n",
        "rubric": [
            {"id": "plot", "type": "plot", "label": "Graficar f en [0,3]", "min_figures": 1, "points": 10},
            {"id": "def_f", "type": "function", "label": "Definir f correctamente", "arg_names": ["x"],
             "ref_body": "np.cos(x) - np.sin(np.exp(x))",
             "test_points": [[0.2], [0.8], [1.5], [2.2], [2.9]], "points": 20},
            {"id": "call_bisect", "type": "call", "label": "Llamar bisect(f, 0.5, 1.0, xtol=1e-8, full_output=True)",
             "qualnames": ["scipy.optimize.bisect"], "strict": True,
             "match_args": [
                 {"position": 0, "name": "f", "ref": "def_f"},
                 {"position": 1, "name": "a", "expected": 0.5},
                 {"position": 2, "name": "b", "expected": 1.0},
                 {"name": "xtol", "expected": 1e-8},
                 {"name": "full_output", "expected": True},
             ], "points": 25},
            {"id": "final_r", "type": "final_value", "label": "Raíz correcta", "variable": "r",
             "expected": v["1.1"]["r"], "tolerance": 1e-6, "points": 20},
            {"id": "final_it", "type": "final_value", "label": "Número de iteraciones", "variable": "iteraciones",
             "expected": v["1.1"]["iters"], "tolerance": 0.5, "points": 12.5},
            {"id": "final_calls", "type": "final_value", "label": "Número de llamadas a f", "variable": "llamadas",
             "expected": v["1.1"]["calls"], "tolerance": 0.5, "points": 12.5},
            {"type": "blocked_call", "qualnames": METODOS_ALTERNOS_RAICES, "points": 0},
        ],
    })

    # ---------------- 1.2 ----------------
    p12 = v["1.2"]
    problems.append({
        "title": "1.2 — Las tres raíces de f(x)=e^x-3x²",
        "statement_md": (
            "Sea $f(x)=e^x-3x^2$, que tiene tres ceros reales.\n\n"
            "1. Grafique $f$ y muestre los tres cambios de signo.\n"
            "2. Aproxime las tres raíces con `bisect` (`xtol=1e-10`, `full_output=True`), usando los "
            f"intervalos $({p12['r1']['a']}, {p12['r1']['b']})$, $({p12['r2']['a']}, {p12['r2']['b']})$ y "
            f"$({p12['r3']['a']}, {p12['r3']['b']})$. Guarde las raíces en `r1`, `r2`, `r3`."
        ),
        "starter_code": "import numpy as np\nimport matplotlib.pyplot as plt\nfrom scipy.optimize import bisect\n\ndef f(x):\n    return np.exp(x) - 3*x**2\n",
        "rubric": [
            {"id": "plot", "type": "plot", "label": "Graficar f", "min_figures": 1, "points": 10},
            {"id": "def_f", "type": "function", "label": "Definir f correctamente", "arg_names": ["x"],
             "ref_body": "np.exp(x) - 3*x**2", "test_points": [[-1.5], [-0.2], [0.5], [1.5], [3.5]], "points": 15},
            *[
                {"id": f"call_{name}", "type": "call", "label": f"Llamar bisect en {name}",
                 "qualnames": ["scipy.optimize.bisect"], "strict": True,
                 "match_args": [{"position": 0, "name": "f", "ref": "def_f"},
                                 {"position": 1, "name": "a", "expected": p12[name]["a"]},
                                 {"position": 2, "name": "b", "expected": p12[name]["b"]}],
                 "points": 10}
                for name in ("r1", "r2", "r3")
            ],
            *[
                {"id": f"final_{name}", "type": "final_value", "label": f"Raíz {name} correcta", "variable": name,
                 "expected": p12[name]["r"], "tolerance": 1e-7, "points": 15}
                for name in ("r1", "r2", "r3")
            ],
            {"type": "blocked_call", "qualnames": METODOS_ALTERNOS_RAICES, "points": 0},
        ],
    })

    # ---------------- 1.3 ----------------
    p13 = v["1.3"]
    problems.append({
        "title": "1.3 — Ceros de f(x)=ln|(1+x)/(1-x²)|",
        "statement_md": (
            "Simplifique $f(x)=\\ln\\left|\\frac{1+x}{1-x^2}\\right|$ (queda $-\\ln|1-x|$, con $x\\neq \\pm1$) "
            "y determine sus dos ceros.\n\n"
            f"Apruxímelos con `bisect` (`xtol=1e-9`) en $({p13['r1']['a']}, {p13['r1']['b']})$ y "
            f"$({p13['r2']['a']}, {p13['r2']['b']})$. Guarde los resultados en `r1` y `r2`.\n\n"
            "Nota: NO se pide en este problema ejecutar `bisect` en $[0.5, 1.5]$ (esa parte, sobre el error "
            "que lanza `scipy` por la singularidad en $x=1$, se evalúa aparte, no aquí)."
        ),
        "starter_code": "import numpy as np\nfrom scipy.optimize import bisect\n\ndef f(x):\n    return np.log(np.abs((1 + x) / (1 - x**2)))\n",
        "rubric": [
            {"id": "def_f", "type": "function", "label": "Definir f correctamente", "arg_names": ["x"],
             "ref_body": "np.log(np.abs((1 + x) / (1 - x**2)))",
             "test_points": [[-0.9], [-0.3], [0.3], [1.3], [1.8]], "points": 20},
            {"id": "call_r1", "type": "call", "label": "Llamar bisect en el primer cero",
             "qualnames": ["scipy.optimize.bisect"], "strict": True,
             "match_args": [{"position": 0, "name": "f", "ref": "def_f"},
                             {"position": 1, "name": "a", "expected": p13["r1"]["a"]},
                             {"position": 2, "name": "b", "expected": p13["r1"]["b"]}], "points": 15},
            {"id": "call_r2", "type": "call", "label": "Llamar bisect en el segundo cero",
             "qualnames": ["scipy.optimize.bisect"], "strict": True,
             "match_args": [{"position": 0, "name": "f", "ref": "def_f"},
                             {"position": 1, "name": "a", "expected": p13["r2"]["a"]},
                             {"position": 2, "name": "b", "expected": p13["r2"]["b"]}], "points": 15},
            {"id": "final_r1", "type": "final_value", "label": "Primer cero correcto (x=0)", "variable": "r1",
             "expected": p13["r1"]["r"], "tolerance": 1e-6, "points": 25},
            {"id": "final_r2", "type": "final_value", "label": "Segundo cero correcto (x=2)", "variable": "r2",
             "expected": p13["r2"]["r"], "tolerance": 1e-6, "points": 25},
            {"type": "blocked_call", "qualnames": METODOS_ALTERNOS_RAICES, "points": 0},
        ],
    })

    # ---------------- 1.4 ----------------
    p14 = v["1.4"]
    problems.append({
        "title": "1.4 — Raíces de cos(e^x-2) = e^x/4 - 2 en [0,3]",
        "statement_md": (
            "Reescriba la ecuación como $f(x)=\\cos(e^x-2)-\\left(\\frac{e^x}{4}-2\\right)=0$ y localice sus "
            "raíces en $[0,3]$.\n\n"
            f"Apruxímelas con `bisect` (`xtol=1e-9`) en $({p14['r1']['a']}, {p14['r1']['b']})$, "
            f"$({p14['r2']['a']}, {p14['r2']['b']})$ y $({p14['r3']['a']}, {p14['r3']['b']})$. "
            "Guarde los resultados en `r1`, `r2`, `r3`."
        ),
        "starter_code": "import numpy as np\nfrom scipy.optimize import bisect\n\ndef f(x):\n    return np.cos(np.exp(x) - 2) - (np.exp(x)/4 - 2)\n",
        "rubric": [
            {"id": "plot", "type": "plot", "label": "Graficar f en [0,3]", "min_figures": 1, "points": 10},
            {"id": "def_f", "type": "function", "label": "Definir f correctamente", "arg_names": ["x"],
             "ref_body": "np.cos(np.exp(x) - 2) - (np.exp(x)/4 - 2)",
             "test_points": [[0.3], [1.0], [1.7], [2.2], [2.8]], "points": 15},
            *[
                {"id": f"call_{name}", "type": "call", "label": f"Llamar bisect en {name}",
                 "qualnames": ["scipy.optimize.bisect"], "strict": True,
                 "match_args": [{"position": 0, "name": "f", "ref": "def_f"},
                                 {"position": 1, "name": "a", "expected": p14[name]["a"]},
                                 {"position": 2, "name": "b", "expected": p14[name]["b"]}],
                 "points": 10}
                for name in ("r1", "r2", "r3")
            ],
            *[
                {"id": f"final_{name}", "type": "final_value", "label": f"Raíz {name} correcta", "variable": name,
                 "expected": p14[name]["r"], "tolerance": 1e-6, "points": 10}
                for name in ("r1", "r2", "r3")
            ],
            {"type": "blocked_call", "qualnames": METODOS_ALTERNOS_RAICES, "points": 0},
        ],
    })

    # ---------------- 1.5 ----------------
    p15 = v["1.5"]
    problems.append({
        "title": "1.5 — Máximo y mínimo de f(x)=e^x·cos(3x)-sin(5x+1) en [-2, 1.5]",
        "statement_md": (
            "Calcule analíticamente $f'(x)$. Grafique $f$ y $f'$ en $[-2, 1.5]$.\n\n"
            "Use `bisect` sobre $f'$ (con los intervalos que identifique en la gráfica) para hallar los "
            "números críticos, y evalúe $f$ en ellos y en los extremos del intervalo para determinar el "
            "**valor máximo** y el **valor mínimo** de $f$ en $[-2,1.5]$. Guárdelos en `fmax` y `fmin`."
        ),
        "starter_code": (
            "import numpy as np\nimport matplotlib.pyplot as plt\nfrom scipy.optimize import bisect\n\n"
            "def f(x):\n    return np.exp(x)*np.cos(3*x) - np.sin(5*x + 1)\n\n"
            "def fprime(x):\n    # su derivada aquí\n    pass\n"
        ),
        "rubric": [
            {"id": "plot", "type": "plot", "label": "Graficar f y f'", "min_figures": 1, "points": 10},
            {"id": "def_fprime", "type": "function", "label": "Derivada f' correcta", "arg_names": ["x"],
             "ref_body": "np.exp(x)*(np.cos(3*x) - 3*np.sin(3*x)) - 5*np.cos(5*x + 1)",
             "test_points": [[-1.8], [-1.1], [-0.4], [0.15], [0.5], [1.25]], "points": 30},
            {"id": "call_bisect_fprime", "type": "call", "label": "Usar bisect sobre f'",
             "qualnames": ["scipy.optimize.bisect"], "strict": True,
             "match_args": [{"position": 0, "name": "f", "ref": "def_fprime"}], "points": 20},
            {"id": "final_fmax", "type": "final_value", "label": "Valor máximo de f correcto", "variable": "fmax",
             "expected": p15["fmax"], "tolerance": 1e-4, "points": 20},
            {"id": "final_fmin", "type": "final_value", "label": "Valor mínimo de f correcto", "variable": "fmin",
             "expected": p15["fmin"], "tolerance": 1e-4, "points": 20},
            {"type": "blocked_call", "qualnames": METODOS_ALTERNOS_RAICES + ["scipy.optimize.minimize_scalar"], "points": 0},
        ],
    })

    # ---------------- 1.6 ----------------
    p16 = v["1.6"]
    problems.append({
        "title": "1.6 — Puntos fijos de h(x)=4sin(x)+eˣ-5 y g(x)=e^(x·cos x)-10·arctan(x³/(x²+1))",
        "statement_md": (
            "Para $h(x)=4\\sin(x)+e^x-5$ y $g(x)=e^{x\\cos(x)}-10\\arctan\\left(\\frac{x^3}{x^2+1}\\right)$: "
            "`scipy.optimize.fixed_point` con `method='iteration'` **no converge** cerca de sus puntos fijos "
            "(la derivada no cumple $|h'|<1$ / $|g'|<1$ ahí).\n\n"
            "Obtenga el punto fijo de $h$ aplicando `bisect` a $x-h(x)$ en $[0.5, 1.5]$, y el de $g$ aplicando "
            "`bisect` a $x-g(x)$ en $[0, 1]$, con `xtol=1e-10`. Guárdelos en `rh` y `rg`."
        ),
        "starter_code": (
            "import numpy as np\nfrom scipy.optimize import bisect\n\n"
            "def h(x):\n    return 4*np.sin(x) + np.exp(x) - 5\n\n"
            "def g(x):\n    return np.exp(x*np.cos(x)) - 10*np.arctan(x**3/(x**2 + 1))\n"
        ),
        "rubric": [
            {"id": "def_h", "type": "function", "label": "Definir h correctamente", "arg_names": ["x"],
             "ref_body": "4*np.sin(x) + np.exp(x) - 5", "test_points": [[0.2], [0.6], [1.0], [1.4]], "points": 10},
            {"id": "def_g", "type": "function", "label": "Definir g correctamente", "arg_names": ["x"],
             "ref_body": "np.exp(x*np.cos(x)) - 10*np.arctan(x**3/(x**2 + 1))",
             "test_points": [[0.1], [0.4], [0.7], [0.9]], "points": 10},
            {"id": "def_diff_h", "type": "function", "label": "(interno) x - h(x)", "arg_names": ["x"],
             "ref_body": "x - (4*np.sin(x) + np.exp(x) - 5)", "test_points": [[0.6], [1.0], [1.4]], "points": 0},
            {"id": "def_diff_g", "type": "function", "label": "(interno) x - g(x)", "arg_names": ["x"],
             "ref_body": "x - (np.exp(x*np.cos(x)) - 10*np.arctan(x**3/(x**2 + 1)))",
             "test_points": [[0.1], [0.4], [0.7]], "points": 0},
            {"id": "call_bisect_h", "type": "call", "label": "bisect sobre x-h(x) en [0.5,1.5]",
             "qualnames": ["scipy.optimize.bisect"], "strict": True,
             "match_args": [{"position": 0, "name": "f", "ref": "def_diff_h"},
                             {"position": 1, "name": "a", "expected": 0.5},
                             {"position": 2, "name": "b", "expected": 1.5}], "points": 20},
            {"id": "call_bisect_g", "type": "call", "label": "bisect sobre x-g(x) en [0,1]",
             "qualnames": ["scipy.optimize.bisect"], "strict": True,
             "match_args": [{"position": 0, "name": "f", "ref": "def_diff_g"},
                             {"position": 1, "name": "a", "expected": 0.0},
                             {"position": 2, "name": "b", "expected": 1.0}], "points": 20},
            {"id": "final_rh", "type": "final_value", "label": "Punto fijo de h correcto", "variable": "rh",
             "expected": p16["rh"], "tolerance": 1e-6, "points": 20},
            {"id": "final_rg", "type": "final_value", "label": "Punto fijo de g correcto", "variable": "rg",
             "expected": p16["rg"], "tolerance": 1e-6, "points": 20},
            {"type": "blocked_call", "qualnames": ["scipy.optimize.fixed_point"] + METODOS_ALTERNOS_RAICES, "points": 0},
        ],
    })

    # ---------------- 1.7 ----------------
    problems.append({
        "title": "1.7 — Punto fijo no trivial de g(x)=x^(x-cos x)",
        "statement_md": (
            "Sea $g(x)=x^{x-\\cos(x)}$ para $x\\geq 0.1$ (nota: $x=1$ es un punto fijo trivial, "
            "$g(1)=1$).\n\n"
            "Encuentre el **otro** punto fijo (no trivial) usando `fixed_point` con el método por defecto "
            "(`method='del2'`, no indique `method`), `xtol=1e-9`, `maxiter=100`, partiendo de $x_0=1.4$. "
            "Guárdelo en `r`."
        ),
        "starter_code": "import numpy as np\nfrom scipy.optimize import fixed_point\n\ndef g(x):\n    return x**(x - np.cos(x))\n",
        "rubric": [
            {"id": "def_g", "type": "function", "label": "Definir g correctamente", "arg_names": ["x"],
             "ref_body": "x**(x - np.cos(x))", "test_points": [[0.5], [0.9], [1.1], [1.3], [1.5]], "points": 30},
            {"id": "call_fp", "type": "call", "label": "Llamar fixed_point(g, 1.4, xtol=1e-9, maxiter=100)",
             "qualnames": ["scipy.optimize.fixed_point"], "strict": True,
             "match_args": [{"position": 0, "name": "func", "ref": "def_g"},
                             {"position": 1, "name": "x0", "expected": 1.4}], "points": 30},
            {"id": "final_r", "type": "final_value", "label": "Punto fijo no trivial correcto", "variable": "r",
             "expected": v["1.7"]["r"], "tolerance": 1e-5, "points": 40},
            {"type": "blocked_call", "qualnames": METODOS_ALTERNOS_RAICES, "points": 0},
        ],
    })

    # ---------------- 1.8 ----------------
    p18 = v["1.8"]
    problems.append({
        "title": "1.8 — Punto fijo de g(x)=2⁻ˣ en [1/3, 1] y cota a priori",
        "statement_md": (
            "Sea $g(x)=2^{-x}$ en $I=[1/3, 1]$.\n\n"
            "1. Calcule $k=\\max_{x\\in I}|g'(x)|$ y guárdelo en `k`.\n"
            "2. Con la cota a priori $|p-p_n|\\leq \\frac{k^n}{1-k}|p_1-p_0|$, $p_0=0.5$, prediga cuántas "
            "iteraciones $n$ se necesitan para `xtol=1e-6` y guárdelo en `n_pred`.\n"
            "3. Aproxime el punto fijo con `fixed_point(g, 0.5, method='iteration', xtol=1e-6, maxiter=200)` "
            "y guárdelo en `punto_fijo`.\n"
            "4. Averigüe el primer `maxiter` (empezando en 1) para el cual la rutina converge sin lanzar "
            "`RuntimeError`, y guárdelo en `maxiter_min`."
        ),
        "starter_code": (
            "import numpy as np\nfrom scipy.optimize import fixed_point\n\n"
            "def g(x):\n    return 2.0**(-x)\n\n# k, n_pred, punto_fijo, maxiter_min\n"
        ),
        "rubric": [
            {"id": "def_g", "type": "function", "label": "Definir g correctamente", "arg_names": ["x"],
             "ref_body": "2.0**(-x)", "test_points": [[0.34], [0.5], [0.7], [1.0]], "points": 15},
            {"id": "final_k", "type": "final_value", "label": "Constante k correcta", "variable": "k",
             "expected": p18["k"], "tolerance": 1e-6, "points": 15},
            {"id": "final_npred", "type": "final_value", "label": "n predicho por la cota a priori",
             "variable": "n_pred", "expected": p18["n_pred"], "tolerance": 0.5, "points": 20},
            {"id": "call_fp", "type": "call", "label": "Llamar fixed_point(g, 0.5, method='iteration', xtol=1e-6, maxiter=200)",
             "qualnames": ["scipy.optimize.fixed_point"], "strict": True,
             "match_args": [{"position": 0, "name": "func", "ref": "def_g"},
                             {"position": 1, "name": "x0", "expected": 0.5},
                             {"name": "method", "expected": "iteration"}], "points": 15},
            {"id": "final_pf", "type": "final_value", "label": "Punto fijo correcto", "variable": "punto_fijo",
             "expected": p18["punto_fijo"], "tolerance": 1e-5, "points": 15},
            {"id": "final_maxiter", "type": "final_value", "label": "maxiter mínimo que converge",
             "variable": "maxiter_min", "expected": p18["maxiter_min"], "tolerance": 0.5, "points": 20},
            {"type": "blocked_call", "qualnames": METODOS_ALTERNOS_RAICES, "points": 0},
        ],
    })

    # ---------------- 1.9 ----------------
    problems.append({
        "title": "1.9 — g₁ del polinomio x³+x²-3x-3, ¿a qué raíz converge?",
        "statement_md": (
            "El polinomio $x^3+x^2-3x-3=0$ tiene tres raíces reales, entre ellas $r=\\sqrt{3}$. Se propone "
            "$g_1(x)=\\frac{x^3+x^2-3}{3}$ (verifique que $r=\\sqrt{3}$ es punto fijo de $g_1$).\n\n"
            "Ejecute `fixed_point(g1, 1.5, method='iteration', xtol=1e-10, maxiter=200)`: **no** converge a "
            "$\\sqrt{3}$. Guarde en `raiz_convergida` el valor al que realmente converge."
        ),
        "starter_code": "import numpy as np\nfrom scipy.optimize import fixed_point\n\ndef g1(x):\n    return (x**3 + x**2 - 3) / 3\n",
        "rubric": [
            {"id": "def_g1", "type": "function", "label": "Definir g1 correctamente", "arg_names": ["x"],
             "ref_body": "(x**3 + x**2 - 3) / 3", "test_points": [[-2.0], [-1.0], [0.5], [1.5], [1.8]], "points": 25},
            {"id": "call_fp", "type": "call", "label": "Llamar fixed_point(g1, 1.5, method='iteration', xtol=1e-10, maxiter=200)",
             "qualnames": ["scipy.optimize.fixed_point"], "strict": True,
             "match_args": [{"position": 0, "name": "func", "ref": "def_g1"},
                             {"position": 1, "name": "x0", "expected": 1.5},
                             {"name": "method", "expected": "iteration"}], "points": 35},
            {"id": "final_r", "type": "final_value", "label": "Identificó a qué raíz converge realmente (-1, no √3)",
             "variable": "raiz_convergida", "expected": v["1.9"]["conv_g1_desde_1_5"], "tolerance": 1e-6, "points": 40},
            {"type": "blocked_call", "qualnames": METODOS_ALTERNOS_RAICES, "points": 0},
        ],
    })

    # ---------------- 1.10 ----------------
    p110 = v["1.10"]
    problems.append({
        "title": "1.10 — Raíz de tan(x)=x cercana a 4.5 (bisect vs. fixed_point)",
        "statement_md": (
            "Sea $f(x)=x-\\tan(x)$. Grafique $f$ en $[4.4, 4.5]$ (cuidado con la asíntota de $\\tan$: no use "
            "$[4.4, 4.8]$).\n\n"
            "1. Aproxime la raíz con `bisect(f, 4.4, 4.5, xtol=1e-12, full_output=True)`. Guarde la raíz en "
            "`r` y las iteraciones en `iteraciones`.\n"
            "2. Aproxime la misma raíz con `fixed_point` sobre $g(x)=\\arctan(x)+\\pi$, `method='iteration'`, "
            "$x_0=4.5$, `xtol=1e-12`, `maxiter=500`. Guárdela en `r_fixed_point`."
        ),
        "starter_code": (
            "import numpy as np\nimport matplotlib.pyplot as plt\nfrom scipy.optimize import bisect, fixed_point\n\n"
            "def f(x):\n    return x - np.tan(x)\n\ndef g(x):\n    return np.arctan(x) + np.pi\n"
        ),
        "rubric": [
            {"id": "plot", "type": "plot", "label": "Graficar f en [4.4,4.5]", "min_figures": 1, "points": 10},
            {"id": "def_f", "type": "function", "label": "Definir f correctamente", "arg_names": ["x"],
             "ref_body": "x - np.tan(x)", "test_points": [[4.41], [4.44], [4.47], [4.49]], "points": 15},
            {"id": "def_g", "type": "function", "label": "Definir g correctamente", "arg_names": ["x"],
             "ref_body": "np.arctan(x) + np.pi", "test_points": [[4.41], [4.47], [4.49]], "points": 10},
            {"id": "call_bisect", "type": "call", "label": "Llamar bisect(f, 4.4, 4.5, xtol=1e-12, full_output=True)",
             "qualnames": ["scipy.optimize.bisect"], "strict": True,
             "match_args": [{"position": 0, "name": "f", "ref": "def_f"},
                             {"position": 1, "name": "a", "expected": 4.4},
                             {"position": 2, "name": "b", "expected": 4.5},
                             {"name": "xtol", "expected": 1e-12}], "points": 20},
            {"id": "call_fp", "type": "call", "label": "Llamar fixed_point(g, 4.5, method='iteration', xtol=1e-12, maxiter=500)",
             "qualnames": ["scipy.optimize.fixed_point"], "strict": True,
             "match_args": [{"position": 0, "name": "func", "ref": "def_g"},
                             {"position": 1, "name": "x0", "expected": 4.5},
                             {"name": "method", "expected": "iteration"}], "points": 10},
            {"id": "final_r", "type": "final_value", "label": "Raíz correcta (bisect)", "variable": "r",
             "expected": p110["r"], "tolerance": 1e-9, "points": 15},
            {"id": "final_it", "type": "final_value", "label": "Número de iteraciones (bisect)",
             "variable": "iteraciones", "expected": p110["iters"], "tolerance": 0.5, "points": 5},
            {"id": "final_rfp", "type": "final_value", "label": "Misma raíz vía fixed_point",
             "variable": "r_fixed_point", "expected": p110["r_fixed_point"], "tolerance": 1e-6, "points": 15},
            {"type": "blocked_call", "qualnames": [
                "scipy.optimize.brentq", "scipy.optimize.newton", "scipy.optimize.fsolve",
                "scipy.optimize.root_scalar", "sympy.nsolve", "sympy.solve",
            ], "points": 0},
        ],
    })

    # ---------------- Sistemas lineales + matrices de iteración ----------------
    s = v["sistemas"]
    problems.append({
        "title": "Sistemas 3x3 — solución directa y matrices de iteración (Jacobi/Gauss-Seidel/SOR)",
        "statement_md": (
            f"Sea el sistema $Ax=b$ con $A={s['A']}$ y $b={s['b']}$.\n\n"
            "1. Resuelva el sistema con `scipy.linalg.solve` y guarde el resultado en `x` (vector de 3 componentes).\n"
            "2. Con $A=D-L-U$ (descomposición estándar: $D$ diagonal, $L$ y $U$ triangulares con signo negativo), "
            "construya y guarde:\n"
            "   - `T_jacobi` $=D^{-1}(L+U)$\n"
            "   - `T_gs` $=(D-L)^{-1}U$\n"
            f"   - `T_sor` $=(D-\\omega L)^{{-1}}\\left((1-\\omega)D+\\omega U\\right)$, con $\\omega={s['omega']}$"
        ),
        "starter_code": (
            "import numpy as np\nfrom scipy.linalg import solve\n\n"
            f"A = np.array({s['A']})\nb = np.array({s['b']})\nomega = {s['omega']}\n\n"
            "x = solve(A, b)\n\nD = np.diag(np.diag(A))\nL = -np.tril(A, -1)\nU = -np.triu(A, 1)\n\n"
            "T_jacobi = None  # D^-1 (L+U)\nT_gs = None       # (D-L)^-1 U\nT_sor = None      # (D-wL)^-1 ((1-w)D + wU)\n"
        ),
        "rubric": [
            {"id": "call_solve", "type": "call", "label": "Usar scipy.linalg.solve",
             "qualnames": ["scipy.linalg.solve"], "strict": False, "points": 15},
            {"id": "final_x", "type": "final_value", "label": "Solución x correcta", "variable": "x",
             "expected": s["x"], "tolerance": 1e-6, "points": 25},
            {"id": "final_Tj", "type": "final_value", "label": "Matriz de iteración de Jacobi correcta",
             "variable": "T_jacobi", "expected": s["T_jacobi"], "tolerance": 1e-6, "points": 20},
            {"id": "final_Tgs", "type": "final_value", "label": "Matriz de iteración de Gauss-Seidel correcta",
             "variable": "T_gs", "expected": s["T_gs"], "tolerance": 1e-6, "points": 20},
            {"id": "final_Tsor", "type": "final_value", "label": f"Matriz de iteración de SOR correcta (ω={s['omega']})",
             "variable": "T_sor", "expected": s["T_sor"], "tolerance": 1e-6, "points": 20},
        ],
    })

    return problems


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bank = db.query(models.ProblemBank).filter_by(title=BANK_TITLE, group=BANK_GROUP).first()
        if not bank:
            bank = models.ProblemBank(title=BANK_TITLE, description="Numerales 1.1-1.10 + sistemas iterativos", group=BANK_GROUP)
            db.add(bank)
            db.flush()
            print(f"Banco creado: {BANK_TITLE!r} (id={bank.id})")
        else:
            print(f"Banco ya existía: {BANK_TITLE!r} (id={bank.id})")

        v = compute_reference_values()
        created, skipped = 0, 0
        for spec in build_problems(v):
            exists = db.query(models.Problem).filter_by(bank_id=bank.id, title=spec["title"]).first()
            if exists:
                skipped += 1
                continue
            db.add(models.Problem(
                bank_id=bank.id,
                title=spec["title"],
                statement_md=spec["statement_md"],
                starter_code=spec["starter_code"],
                status="draft",
                rubric=json.dumps(spec["rubric"]),
            ))
            created += 1
        db.commit()
        print(f"Problemas creados: {created}. Ya existían (omitidos): {skipped}.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
