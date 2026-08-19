"""Siembra los bancos de problemas para "Parcial Práctico Dos", a partir de los
.tex de Moodle en Problemas_Parcial2/ (Integrales.tex, PVIs.tex, EDPs.tex).

Cada .tex original calificaba solo por valores numéricos finales (estilo
Moodle cloze). Aquí, además del valor final, se exige también verificar el
código: que el estudiante defina correctamente las funciones involucradas y
llame la rutina del curso correcta con los argumentos correctos (igual que
en seed_taller.py para el Simulacro).

Uso: python -m app.seed_parcial2
"""
import json

from .database import SessionLocal, engine, Base
from . import models

TP = lambda *vals: [[v] for v in vals]  # test_points de una sola variable


# ---------------------------------------------------------------------------
# Banco 1 — Integrales impropias (sustitución x=1/t + cuadratura Gaussiana 3 nodos)
# ---------------------------------------------------------------------------
#
# Las 5 variantes son la misma f(x) = e^{-d^2} sin(d) / (d*sqrt(d^2+1)) con
# d = x - shift, escalada por `coef` — f tiene una única singularidad
# removible, en x = shift. El valor analítico exacto (verificado con
# scipy.integrate.quad, alta precisión) es coef * K con K = 1.429567931170479.
#
# Diseño: los límites externos son SIEMPRE -1 y 1 (para las 5 variantes),
# de modo que la sustitución canónica vista en clase, x=1/t para [1,∞) y
# x=-1/t para (-∞,-1], aplica igual en todas. shift se mantiene siempre
# estrictamente dentro de (-1,1) para que el único punto de quiebre a
# encontrar (A) sea la singularidad misma:
#   ∫_{-∞}^{-1} f dx + ∫_{-1}^{A} f dx + ∫_{A}^{1} f dx + ∫_{1}^{∞} f dx
#
# El .tex original de Moodle daba como "correcto" el resultado de un método
# de sustitución no documentado (los valores no escalaban linealmente con
# coef, lo que confirma que no era el valor analítico). Por eso `expected`
# se calibra contra el valor analítico real; con x=1/t fijo la aproximación
# de Gauss-3 tiene un error de hasta ~0.08 respecto al valor exacto (mayor
# cuanto más cerca esté la singularidad de ±1), así que se usa tolerancia 0.1.

K_INTEGRAL = 1.429567931170479


def integrales_problem(idx, shift, coef):
    expected_final = coef * K_INTEGRAL

    shift_str = f"x - {shift}" if shift >= 0 else f"x + {-shift}"
    d_tex = "x" if shift == 0 else (f"(x-{shift})" if shift > 0 else f"(x+{-shift})")
    ref_body = f"{coef}*np.exp(-({shift_str})**2)*np.sin({shift_str})/(({shift_str})*np.sqrt(({shift_str})**2+1))"
    tp = [[v] for v in (-0.9, -0.6, -0.3, 0.2, 0.4, 0.7, 0.9) if abs(v - shift) > 0.05]

    if coef == 1:
        f_tex = rf"\frac{{e^{{-{d_tex}^2}}\sin({d_tex})}}{{{d_tex}\sqrt{{{d_tex}^2+1}}}}"
    else:
        f_tex = rf"\frac{{{coef}e^{{-{d_tex}^2}}\sin({d_tex})}}{{{d_tex}\sqrt{{{d_tex}^2+1}}}}"

    statement = rf"""
## Integral impropia con sustitución + cuadratura Gaussiana (variante {idx})

Considere la integral

$$
\int_{{-\infty}}^{{\infty}} f(x)\, dx, \qquad f(x) = {f_tex}
$$

Esta $f$ tiene una única singularidad removible, en un punto $A\in(-1,1)$
(el límite de $f$ ahí existe, pero la expresión da $0/0$). La integral se
debe escribir de la forma

$$
\int_{{-\infty}}^{{-1}}f(x)dx + \int_{{-1}}^{{A}}f(x)dx+ \int_{{A}}^{{1}}f(x)dx+ \int_{{1}}^{{\infty}}f(x)dx
$$

### Instrucciones

1. Encuentre el punto de singularidad $A$ y guárdelo en la variable **`A`**.
2. Defina $f(x)$ como una función de Python que también maneje ese punto
   (evalúe el límite ahí, no la expresión original que da $0/0$).
3. Para las dos colas infinitas use la sustitución vista en clase:
   $x = 1/t$ para $[1,\infty)$ y $x=-1/t$ para $(-\infty,-1]$, con $t\in(0,1]$.
4. Calcule **cada una** de las cuatro integrales (las dos colas ya
   sustituidas y los dos tramos finitos) con cuadratura de Gauss de **3
   nodos**, y súmelas para obtener la integral definitiva. Guarde el
   resultado en **`I_final`** (ya declarada).

**Nota sobre la tolerancia:** la aproximación con solo 3 nodos por tramo
tiene un error de truncamiento; por eso el valor final se califica con una
tolerancia más amplia que las demás variables.

### Calificación (100 puntos)
- 20 pts — definir correctamente $f(x)$ (incluyendo el punto de singularidad removible).
- 10 pts — usar cuadratura de Gauss con 3 nodos.
- 20 pts — valor de A (punto de singularidad) correcto.
- 50 pts — valor final de `I_final` correcto (tolerancia amplia, ver nota arriba).
"""

    starter = (
        "A = None  # No modificar el nombre de esta variable\n"
        "I_final = None  # No modificar el nombre de esta variable\n"
    )

    rubric = [
        {"id": "def_f", "type": "function", "label": "Definir correctamente el integrando f(x)",
         "arg_names": ["x"], "ref_body": ref_body, "test_points": tp, "points": 20},
        {"id": "call_gauss", "type": "call", "label": "Usar cuadratura de Gauss con 3 nodos",
         "qualnames": ["CuadGaussLegendre.CuadGaussLegendre"], "strict": False, "points": 10},
        {"id": "final_A", "type": "final_value", "label": "Punto de singularidad A correcto",
         "variable": "A", "expected": shift, "tolerance": 1e-6, "points": 20},
        {"id": "final_I", "type": "final_value", "label": "Valor final de la integral (I_final) correcto",
         "variable": "I_final", "expected": expected_final, "tolerance": 0.1, "points": 50},
    ]

    solution = f'''import numpy as np
from CuadGaussLegendre import CuadGaussLegendre

def f(x):
    x = np.asarray(x, dtype=float)
    d = x - ({shift})
    safe_d = np.where(np.abs(d) < 1e-9, 1.0, d)
    val = {coef} * np.exp(-d**2) * np.sin(d) / safe_d / np.sqrt(d**2 + 1)
    val = np.where(np.abs(d) < 1e-9, {coef} * np.exp(-d**2) / np.sqrt(d**2 + 1), val)
    return val if val.ndim else float(val)

A = {shift}

def tail_izq(t):
    x = -1 / t
    return f(x) * (1 / t**2)

def tail_der(t):
    x = 1 / t
    return f(x) * (1 / t**2)

I_final = CuadGaussLegendre(tail_izq, 1e-9, 1, 3)[0]
I_final += CuadGaussLegendre(f, -1, A, 3)[0]
I_final += CuadGaussLegendre(f, A, 1, 3)[0]
I_final += CuadGaussLegendre(tail_der, 1e-9, 1, 3)[0]
'''
    return dict(
        title=f"Integral impropia con sustitución (variante {idx})",
        statement_md=statement, starter_code=starter, rubric=rubric, solution_code=solution,
    )


INTEGRALES_VARIANTS = [
    dict(idx=1, shift=0, coef=1),
    dict(idx=2, shift=0.3, coef=2),
    dict(idx=3, shift=-0.3, coef=3),
    dict(idx=4, shift=0.6, coef=2),
    dict(idx=5, shift=-0.5, coef=4),
]

INTEGRALES_PROBLEMS = [lambda kw=kw: integrales_problem(**kw) for kw in INTEGRALES_VARIANTS]


# ---------------------------------------------------------------------------
# Banco 2 — P.V.I. y P.V.F. (Euler modificado/RK4, diferencias finitas, disparo
# lineal, sistemas de orden superior)
# ---------------------------------------------------------------------------
#
# NOTA sobre 2 variantes del .tex original que se ajustaron tras verificar
# cada valor con las rutinas del curso (y, en casos de duda, con un solver
# independiente de alta precisión, scipy.integrate.solve_ivp):
#
# - La variante del P.V.F. con coeficientes e^{2x} en [0,3] traía en el .tex
#   un segundo valor (disparo lineal en x=1.5) que resultó numéricamente
#   inalcanzable: el método de disparo lineal (RK4 explícito hacia adelante)
#   diverge en ese dominio porque los coeficientes crecen como e^{2x} (~400
#   en x=3), y ni ese método ni diferencias finitas reproducen el valor del
#   .tex. Se dejó solo la parte de diferencias finitas (que sí es estable y
#   coincide exacto con el .tex) y se retiró el sub-problema de disparo.
# - La variante del P.V.I. de orden 3 en [0,2] (y'''=4y'+sin(x)e^x y+3) traía
#   en el .tex valores que no coinciden ni con RK4_sist del curso ni con
#   scipy en alta precisión (que sí concuerdan entre sí); se excluyó del
#   banco por tener el enunciado original un error de cálculo no resoluble
#   sin más contexto.


TP2 = lambda *pairs: [list(p) for p in pairs]


def pvi_euler_rk4_problem(idx, coef_desc, f_desc, f_ref_body, a, target, ya, M, expected_em, expected_rk4, tp):
    statement = rf"""
## P.V.I. — Euler modificado y RK4 (variante {idx})

Considere el P.V.I.

$$
{coef_desc}, \qquad {a} \le t \le {target}, \qquad y({a}) = {ya}
$$

Aproxime la solución con tamaño de paso $h=({target}-{a})/{M}=0.1$ empleando los
métodos de **Euler modificado** y **Runge-Kutta de orden 4 (RK4)**.

### Instrucciones

1. Despeje $y'(t)$ de la ecuación y defina $f(t,y)={f_desc}$ como función de Python.
2. Use la rutina del curso para el método de **Euler modificado**, llamada
   como `metodo(f, {a}, {target}, {ya}, {M})` (con $M={M}$ pasos, de modo que
   $h=({target}-{a})/{M}$), y la rutina para **RK4**, con la misma firma.
3. Guarde $y({target})$ de cada método en **`y_eulermod`** y **`y_rk4`** (ya declaradas).

### Calificación (100 puntos)
- 20 pts — definir correctamente f(t,y).
- 15 pts — llamar correctamente el método de Euler modificado.
- 25 pts — valor final de y_eulermod correcto.
- 15 pts — llamar correctamente RK4.
- 25 pts — valor final de y_rk4 correcto.
"""
    starter = (
        "y_eulermod = None  # No modificar el nombre de esta variable\n"
        "y_rk4 = None       # No modificar el nombre de esta variable\n"
    )
    rubric = [
        {"id": "def_f", "type": "function", "label": "Definir correctamente f(t,y)",
         "arg_names": ["t", "y"], "ref_body": f_ref_body, "test_points": tp, "points": 20},
        {"id": "call_em", "type": "call", "label": f"Llamar RK2_EulerMod(f,{a},{target},{ya},{M}) correctamente",
         "qualnames": ["RK2_EulerMod.RK2_EulerMod"], "strict": True,
         "match_args": [{"position": 0, "name": "f", "ref": "def_f"}, {"position": 1, "name": "a", "expected": a},
                         {"position": 2, "name": "b", "expected": target}, {"position": 3, "name": "ya", "expected": ya},
                         {"position": 4, "name": "M", "expected": M}], "points": 15},
        {"id": "final_em", "type": "final_value", "label": "Valor final de y_eulermod correcto",
         "variable": "y_eulermod", "expected": expected_em, "tolerance": 1e-2, "points": 25},
        {"id": "call_rk4", "type": "call", "label": f"Llamar RK4(f,{a},{target},{ya},{M}) correctamente",
         "qualnames": ["RK4.RK4"], "strict": True,
         "match_args": [{"position": 0, "name": "f", "ref": "def_f"}, {"position": 1, "name": "a", "expected": a},
                         {"position": 2, "name": "b", "expected": target}, {"position": 3, "name": "ya", "expected": ya},
                         {"position": 4, "name": "M", "expected": M}], "points": 15},
        {"id": "final_rk4", "type": "final_value", "label": "Valor final de y_rk4 correcto",
         "variable": "y_rk4", "expected": expected_rk4, "tolerance": 1e-2, "points": 25},
    ]
    solution = f'''import numpy as np
from RK2_EulerMod import RK2_EulerMod
from RK4 import RK4

def f(t, y):
    return {f_ref_body}

y_eulermod = RK2_EulerMod(f, {a}, {target}, {ya}, {M})[-1, 1]
y_rk4 = RK4(f, {a}, {target}, {ya}, {M})[-1, 1]
'''
    return dict(title=f"P.V.I. — Euler modificado y RK4 (variante {idx})", statement_md=statement,
                starter_code=starter, rubric=rubric, solution_code=solution)


def pvi1():
    tp = TP2([1.1, 3.5], [1.4, 2.0], [1.7, 4.0], [1.2, 1.0], [1.9, 0.5])
    return pvi_euler_rk4_problem(
        1, r"\arctan(t)\,y'(t) - 5\sin(y(t)) = 1", r"\dfrac{1+5\sin(y)}{\arctan(t)}",
        "(1 + 5*np.sin(y)) / np.arctan(t)", 1, 1.6, 4, 6,
        3.377983405826503, 3.371418605523742, tp,
    )


def pvi2():
    tp = TP2([1.1, 2.0], [1.3, 1.5], [1.5, 0.5], [1.2, 3.0], [1.8, -0.5])
    return pvi_euler_rk4_problem(
        2, r"e^{-t}\,y'(t) - 3\cos(y(t)) = t", r"(t+3\cos(y))e^{t}",
        "(t + 3*np.cos(y)) * np.exp(t)", 1, 1.6, 2, 6,
        2.103519488012695, 2.1011591579393456, tp,
    )


def pvi3():
    tp = TP2([0.1, 2.5], [0.3, 1.5], [0.5, 0.5], [0.2, 3.5], [0.8, -0.5])
    return pvi_euler_rk4_problem(
        3, r"\sqrt{t+1}\,y'(t) - 2\sin(y(t)) = t^2", r"\dfrac{t^2+2\sin(y)}{\sqrt{t+1}}",
        "(t**2 + 2*np.sin(y)) / np.sqrt(t+1)", 0, 0.6, 3, 6,
        3.140412016168486, 3.1397838012964496, tp,
    )


def pvf4():
    statement = r"""
## P.V.F. lineal — diferencias finitas y disparo lineal (variante 4)

Aproxime la solución del P.V.F.

$$
\begin{cases}
e^{-x}y''(x) + xy'(x) - \arctan(x)y(x) = 1+4x, & 1 \le x \le 4,\\
y(1)=0, \quad y(4)=4.
\end{cases}
$$

### Instrucciones

1. Reescriba la ecuación en la forma $y'' = p(x)y' + q(x)y + r(x)$ (dividiendo
   por $e^{-x}$) y defina `p`, `q`, `r`:
$$
p(x) = -xe^{x}, \qquad q(x) = \arctan(x)e^{x}, \qquad r(x) = (1+4x)e^{x}
$$
2. Use la rutina del curso para **diferencias finitas** en P.V.F. lineales,
   llamada como `metodo(p, q, r, 1, 4, 0, 4, 100)` ($h=(4-1)/100=0.03$), y
   guarde en **`y_13`** el valor de $y(1.3)$.
3. Para el **disparo lineal** escriba `F1` (no homogéneo) y `F2` (homogéneo) con
   estado $U=[y,y']$:
   - `F1(x, U) = [U[1], p(x)U[1]+q(x)U[0]+r(x)]`
   - `F2(x, U) = [U[1], p(x)U[1]+q(x)U[0]]`
   Use la rutina correspondiente, llamada como
   `metodo(F1, F2, 1, 4, 0, 4, 100)`, y guarde en **`y_16`** el valor de $y(1.6)$.

### Calificación (100 puntos)
- 10 pts c/u — definir p(x), q(x), r(x) (30 pts).
- 10 pts — llamar correctamente el método de diferencias finitas.
- 20 pts — valor final de y_13 correcto.
- 5 pts c/u — definir F1, F2 (10 pts).
- 10 pts — llamar correctamente el método de disparo lineal.
- 20 pts — valor final de y_16 correcto.
"""
    starter = (
        "y_13 = None  # No modificar el nombre de esta variable\n"
        "y_16 = None  # No modificar el nombre de esta variable\n"
    )
    tp_pqr = [[v] for v in (1.1, 1.5, 2.0, 2.5, 3.0, 3.5, 3.9)]
    tp_sys = [[1.2, [0.5, -0.3]], [1.8, [1.0, 0.2]], [2.5, [-0.5, 0.8]]]
    rubric = [
        {"id": "def_p", "type": "function", "label": "Definir correctamente p(x)", "arg_names": ["x"],
         "ref_body": "-x*np.exp(x)", "test_points": tp_pqr, "points": 10},
        {"id": "def_q", "type": "function", "label": "Definir correctamente q(x)", "arg_names": ["x"],
         "ref_body": "np.arctan(x)*np.exp(x)", "test_points": tp_pqr, "points": 10},
        {"id": "def_r", "type": "function", "label": "Definir correctamente r(x)", "arg_names": ["x"],
         "ref_body": "(1+4*x)*np.exp(x)", "test_points": tp_pqr, "points": 10},
        {"id": "call_diffin", "type": "call", "label": "Llamar Diffin_PVF(p,q,r,1,4,0,4,100) correctamente",
         "qualnames": ["Diffin_PVF.Diffin_PVF"], "strict": True,
         "match_args": [{"position": 0, "name": "p", "ref": "def_p"}, {"position": 1, "name": "q", "ref": "def_q"},
                         {"position": 2, "name": "r", "ref": "def_r"}, {"position": 3, "name": "a", "expected": 1},
                         {"position": 4, "name": "b", "expected": 4}, {"position": 5, "name": "alpha", "expected": 0},
                         {"position": 6, "name": "beta", "expected": 4}, {"position": 7, "name": "N", "expected": 100}],
         "points": 10},
        {"id": "final_diffin", "type": "final_value", "label": "Valor final de y_13 correcto", "variable": "y_13",
         "expected": -3.9791952258158525, "tolerance": 1e-2, "points": 20},
        {"id": "def_F1", "type": "function", "label": "Definir correctamente F1(x,U) (no homogéneo)",
         "arg_names": ["x", "U"],
         "ref_body": "[U[1], -x*np.exp(x)*U[1] + np.arctan(x)*np.exp(x)*U[0] + (1+4*x)*np.exp(x)]",
         "test_points": tp_sys, "points": 5},
        {"id": "def_F2", "type": "function", "label": "Definir correctamente F2(x,U) (homogéneo)",
         "arg_names": ["x", "U"],
         "ref_body": "[U[1], -x*np.exp(x)*U[1] + np.arctan(x)*np.exp(x)*U[0]]",
         "test_points": tp_sys, "points": 5},
        {"id": "call_disparo", "type": "call", "label": "Llamar DisparoLin(F1,F2,1,4,0,4,100) correctamente",
         "qualnames": ["DisparoLin.DisparoLin"], "strict": True,
         "match_args": [{"position": 0, "name": "F1", "ref": "def_F1"}, {"position": 1, "name": "F2", "ref": "def_F2"},
                         {"position": 2, "name": "a", "expected": 1}, {"position": 3, "name": "b", "expected": 4},
                         {"position": 4, "name": "alpha", "expected": 0}, {"position": 5, "name": "beta", "expected": 4},
                         {"position": 6, "name": "M", "expected": 100}], "points": 10},
        {"id": "final_disparo", "type": "final_value", "label": "Valor final de y_16 correcto", "variable": "y_16",
         "expected": -15.53339249836538, "tolerance": 1e-1, "points": 20},
    ]
    solution = '''import numpy as np
from Diffin_PVF import Diffin_PVF
from DisparoLin import DisparoLin

def p(x):
    return -x*np.exp(x)

def q(x):
    return np.arctan(x)*np.exp(x)

def r(x):
    return (1+4*x)*np.exp(x)

F = Diffin_PVF(p, q, r, 1, 4, 0, 4, 100)
y_13 = F[10, 1]

def F1(x, U):
    return [U[1], p(x)*U[1] + q(x)*U[0] + r(x)]

def F2(x, U):
    return [U[1], p(x)*U[1] + q(x)*U[0]]

L = DisparoLin(F1, F2, 1, 4, 0, 4, 100)
y_16 = L[20, 1]
'''
    return dict(title="P.V.F. lineal — diferencias finitas y disparo lineal (variante 4)",
                statement_md=statement, starter_code=starter, rubric=rubric, solution_code=solution)


def pvf5():
    statement = r"""
## P.V.F. lineal — diferencias finitas (variante 5)

Aproxime la solución del P.V.F.

$$
\begin{cases}
e^{-2x}y''(x) + x^2y'(x) - \arctan(x)y(x) = 2+3x, & 0 \le x \le 3,\\
y(0)=1, \quad y(3)=5.
\end{cases}
$$

### Instrucciones

1. Reescriba la ecuación en la forma $y'' = p(x)y' + q(x)y + r(x)$ (dividiendo
   por $e^{-2x}$) y defina `p`, `q`, `r`:
$$
p(x) = -x^2e^{2x}, \qquad q(x) = \arctan(x)e^{2x}, \qquad r(x) = (2+3x)e^{2x}
$$
2. Use la rutina del curso para **diferencias finitas** en P.V.F. lineales,
   llamada como `metodo(p, q, r, 0, 3, 1, 5, 100)` ($h=(3-0)/100=0.03$), y
   guarde en **`y_09`** el valor de $y(0.9)$.

**Nota:** este P.V.F. tiene coeficientes que crecen muy rápido ($e^{2x}$); el
método del disparo lineal (RK4 explícito hacia adelante) es numéricamente
inestable en este dominio y por eso no se pide aquí — solo diferencias finitas,
que es un método estable para este problema.

### Calificación (100 puntos)
- 15 pts c/u — definir p(x), q(x), r(x) (45 pts).
- 15 pts — llamar correctamente el método de diferencias finitas.
- 40 pts — valor final de y_09 correcto.
"""
    starter = "y_09 = None  # No modificar el nombre de esta variable\n"
    tp_pqr = [[v] for v in (0.2, 0.7, 1.2, 1.7, 2.2, 2.7, 2.9)]
    rubric = [
        {"id": "def_p", "type": "function", "label": "Definir correctamente p(x)", "arg_names": ["x"],
         "ref_body": "-x**2*np.exp(2*x)", "test_points": tp_pqr, "points": 15},
        {"id": "def_q", "type": "function", "label": "Definir correctamente q(x)", "arg_names": ["x"],
         "ref_body": "np.arctan(x)*np.exp(2*x)", "test_points": tp_pqr, "points": 15},
        {"id": "def_r", "type": "function", "label": "Definir correctamente r(x)", "arg_names": ["x"],
         "ref_body": "(2+3*x)*np.exp(2*x)", "test_points": tp_pqr, "points": 15},
        {"id": "call_diffin", "type": "call", "label": "Llamar Diffin_PVF(p,q,r,0,3,1,5,100) correctamente",
         "qualnames": ["Diffin_PVF.Diffin_PVF"], "strict": True,
         "match_args": [{"position": 0, "name": "p", "ref": "def_p"}, {"position": 1, "name": "q", "ref": "def_q"},
                         {"position": 2, "name": "r", "ref": "def_r"}, {"position": 3, "name": "a", "expected": 0},
                         {"position": 4, "name": "b", "expected": 3}, {"position": 5, "name": "alpha", "expected": 1},
                         {"position": 6, "name": "beta", "expected": 5}, {"position": 7, "name": "N", "expected": 100}],
         "points": 15},
        {"id": "final_diffin", "type": "final_value", "label": "Valor final de y_09 correcto", "variable": "y_09",
         "expected": -1.0305873485139327, "tolerance": 1e-2, "points": 40},
    ]
    solution = '''import numpy as np
from Diffin_PVF import Diffin_PVF

def p(x):
    return -x**2*np.exp(2*x)

def q(x):
    return np.arctan(x)*np.exp(2*x)

def r(x):
    return (2+3*x)*np.exp(2*x)

F = Diffin_PVF(p, q, r, 0, 3, 1, 5, 100)
y_09 = F[30, 1]
'''
    return dict(title="P.V.F. lineal — diferencias finitas (variante 5)",
                statement_md=statement, starter_code=starter, rubric=rubric, solution_code=solution)


def pvi6():
    statement = r"""
## P.V.I. de orden superior — sistema con RK4 (variante 6)

Considere el P.V.I.

$$
y'''(x) = 5y'(x) + \arctan(x)e^{x}y(x) + 4, \qquad 1 \le x \le 3,
$$
$$
y(1)=1, \quad y'(1)=1, \quad y''(1)=1.
$$

Aproxime la solución empleando **Runge-Kutta de orden 4** con $h=0.1$.

### Instrucciones

1. Escriba el sistema de primer orden con estado $U=[y,y',y'']$, de modo que
   $U' = [\,y',\; y'',\; 5y'+\arctan(x)e^{x}y+4\,]$. Defina `F(x, U)` que retorne esa lista.
2. Use la rutina del curso para **RK4 de sistemas**, llamada como
   `metodo(F, 1, 1.5, [1,1,1], 5)` ($M=5$, ya que $h=(1.5-1)/5=0.1$).
3. Guarde en **`y_15`**, **`yp_15`**, **`ypp_15`** los valores de $y(1.5)$,
   $y'(1.5)$, $y''(1.5)$ (componentes 0, 1, 2 del último paso).

### Calificación (100 puntos)
- 25 pts — definir correctamente F(x, U).
- 25 pts — llamar correctamente el método de RK4 para sistemas.
- 20 pts — valor final de y_15 correcto.
- 15 pts — valor final de yp_15 correcto.
- 15 pts — valor final de ypp_15 correcto.
"""
    starter = (
        "y_15 = None    # No modificar el nombre de esta variable\n"
        "yp_15 = None   # No modificar el nombre de esta variable\n"
        "ypp_15 = None  # No modificar el nombre de esta variable\n"
    )
    tp = [[1.1, [0.5, -0.3, 0.2]], [1.8, [1.0, 0.2, -0.5]], [2.5, [-0.5, 0.8, 1.0]], [2.9, [0.2, -0.7, 0.4]]]
    rubric = [
        {"id": "def_F", "type": "function", "label": "Definir correctamente F(x, U)", "arg_names": ["x", "U"],
         "ref_body": "[U[1], U[2], 5*U[1] + np.arctan(x)*np.exp(x)*U[0] + 4]", "test_points": tp, "points": 25},
        {"id": "call_correct", "type": "call", "label": "Llamar RK4_sist(F,1,1.5,[1,1,1],5) correctamente",
         "qualnames": ["RK4_sist.RK4_sist"], "strict": True,
         "match_args": [{"position": 0, "name": "F", "ref": "def_F"}, {"position": 1, "name": "a", "expected": 1},
                         {"position": 2, "name": "b", "expected": 1.5}, {"position": 3, "name": "Za", "expected": [1, 1, 1]},
                         {"position": 4, "name": "M", "expected": 5}], "points": 25},
        {"id": "final_y", "type": "final_value", "label": "Valor final de y_15 correcto", "variable": "y_15",
         "expected": 1.9056158139896877, "tolerance": 1e-2, "points": 20},
        {"id": "final_yp", "type": "final_value", "label": "Valor final de yp_15 correcto", "variable": "yp_15",
         "expected": 3.3322399131381193, "tolerance": 1e-2, "points": 15},
        {"id": "final_ypp", "type": "final_value", "label": "Valor final de ypp_15 correcto", "variable": "ypp_15",
         "expected": 9.767559528333557, "tolerance": 1e-2, "points": 15},
    ]
    solution = '''import numpy as np
from RK4_sist import RK4_sist

def F(x, U):
    return [U[1], U[2], 5*U[1] + np.arctan(x)*np.exp(x)*U[0] + 4]

T, Z = RK4_sist(F, 1, 1.5, [1, 1, 1], 5)
y_15 = Z[-1, 0]
yp_15 = Z[-1, 1]
ypp_15 = Z[-1, 2]
'''
    return dict(title="P.V.I. de orden superior — sistema con RK4 (variante 6)",
                statement_md=statement, starter_code=starter, rubric=rubric, solution_code=solution)


PVI_PROBLEMS = [pvi1, pvi2, pvi3, pvf4, pvf5, pvi6]


# ---------------------------------------------------------------------------
# Banco 3 — EDP parabólica (estabilidad + diferencias finitas progresivas)
# ---------------------------------------------------------------------------
#
# Las 7 variantes son la misma EDP u_t = 4 u_xx, x en (0,1), t en [0,1],
# u(0,t)=e^{-t}, u(1,t)=sin(t), u(x,0)=x(1-x); solo cambia el punto espacial
# x_i (i=1..7, es decir x=0.1,...,0.7) donde se evalúa u(x_i, 0.125). Se
# verificaron los 7 valores con DifAdelante del curso y coinciden con el .tex
# (diferencia < 0.0006 en todos los casos, dentro de la tolerancia 0.003).

EDP_EXPECTED_U = {
    1: 0.8082215994219295,
    2: 0.7323948200364856,
    3: 0.6551795371414773,
    4: 0.5776574615255062,
    5: 0.4996172099631266,
    6: 0.422330050564168,
    7: 0.34546678038841366,
}


def edp_problem(i):
    x_i = round(i * 0.1, 1)
    expected_u = EDP_EXPECTED_U[i]

    statement = rf"""
## EDP parabólica — estabilidad y diferencias finitas progresivas (variante {i})

Considere la EDP parabólica

$$
\begin{{cases}}
\dfrac{{\partial u}}{{\partial t}} = 4\dfrac{{\partial^2 u}}{{\partial x^2}}, & x\in(0,1),\ t\in[0,1] \\
u(0,t) = e^{{-t}}, \quad u(1,t)=\sin(t) \\
u(x,0) = x(1-x)
\end{{cases}}
$$

**(a)** Se desea emplear el método de diferencias finitas **progresivo**
(adelante en tiempo, centrado en espacio) para aproximar la solución. Si
$h=1/10$, determine el máximo valor de $k$ para que el esquema sea estable.

**(b)** Con esos $h,k$, aproxime la solución con el esquema adelante en
tiempo y dé un valor aproximado para $u(x_{i},\ 0.125)$, con $x_{i}={x_i}$.

### Instrucciones

1. Guarde el valor máximo de $k$ (con $c^2=4$, la estabilidad exige
   $r = c^2 k/h^2 \le 1/2$) en **`k_max`**.
2. Defina $u(x,0)=x(1-x)$, $u(0,t)=e^{{-t}}$, $u(1,t)=\sin(t)$ como funciones de Python.
3. Use la rutina del curso para el esquema **adelante en tiempo** (diferencias
   finitas progresivas), llamada como
   `metodo(f, g1, g2, a=1, b=100*k_max, c=2, n=11, m=101)` — con `n=11`
   nodos espaciales ($h=1/10$) y `m=101` pasos de tiempo, suficientes para
   llegar exactamente a $t=0.125$ con $k=k_{{max}}$.
4. Guarde $u(x_{i}, 0.125)$ en **`u_val`** (columna {i} de la tabla que
   retorna el método, en el último paso de tiempo).

### Calificación (100 puntos)
- 15 pts — valor de k_max correcto.
- 15 pts — definir correctamente u(x,0) = x(1-x).
- 15 pts — definir correctamente u(0,t) = e^(-t).
- 15 pts — definir correctamente u(1,t) = sin(t).
- 20 pts — llamar correctamente el método adelante en tiempo.
- 20 pts — valor final de u_val correcto.
"""
    starter = (
        "k_max = None  # No modificar el nombre de esta variable\n"
        "u_val = None  # No modificar el nombre de esta variable\n"
    )
    tp_ic = [[0.1], [0.3], [0.5], [0.7], [0.9]]
    tp_t = [[0.02], [0.05], [0.08], [0.12]]
    rubric = [
        {"id": "final_kmax", "type": "final_value", "label": "Valor de k_max correcto",
         "variable": "k_max", "expected": 0.00125, "tolerance": 1e-6, "points": 15},
        {"id": "def_ic", "type": "function", "label": "Definir correctamente u(x,0) = x(1-x)",
         "arg_names": ["x"], "ref_body": "x*(1-x)", "test_points": tp_ic, "points": 15},
        {"id": "def_g1", "type": "function", "label": "Definir correctamente u(0,t) = e^(-t)",
         "arg_names": ["t"], "ref_body": "np.exp(-t)", "test_points": tp_t, "points": 15},
        {"id": "def_g2", "type": "function", "label": "Definir correctamente u(1,t) = sin(t)",
         "arg_names": ["t"], "ref_body": "np.sin(t)", "test_points": tp_t, "points": 15},
        {"id": "call_adelante", "type": "call", "label": "Llamar DifAdelante correctamente",
         "qualnames": ["DifAdelante.DifAdelante"], "strict": True,
         "match_args": [{"position": 0, "name": "f", "ref": "def_ic"}, {"position": 1, "name": "g1", "ref": "def_g1"},
                         {"position": 2, "name": "g2", "ref": "def_g2"}, {"position": 3, "name": "a", "expected": 1},
                         {"position": 5, "name": "c", "expected": 2}, {"position": 6, "name": "n", "expected": 11}],
         "points": 20},
        {"id": "final_u", "type": "final_value", "label": "Valor final de u_val correcto",
         "variable": "u_val", "expected": expected_u, "tolerance": 3e-3, "points": 20},
    ]
    solution = f'''import numpy as np
from DifAdelante import DifAdelante

k_max = 0.00125

def f(x):
    return x * (1 - x)

def g1(t):
    return np.exp(-t)

def g2(t):
    return np.sin(t)

U = DifAdelante(f, g1, g2, 1, 100 * k_max, 2, 11, 101)
u_val = U[-1, {i}]
'''
    return dict(title=f"EDP parabólica — estabilidad y diferencias finitas (variante {i})",
                statement_md=statement, starter_code=starter, rubric=rubric, solution_code=solution)


EDP_PROBLEMS = [lambda i=i: edp_problem(i) for i in range(1, 8)]


# ---------------------------------------------------------------------------
# Siembra: 3 bancos + examen "Parcial Práctico Dos" en dos sesiones, cada una
# tomando una variante distinta de cada banco (misma dificultad, distintos
# números) para que la sesión 2 no se beneficie de filtraciones de la 1.
#
# Miércoles 5 de agosto de 2026 — sesión 1: 10:00-10:50, sesión 2: 11:00-11:50
# (hora Colombia). La plataforma no impone ventanas horarias: el docente
# controla el acceso a cada sesión operativamente; duration_minutes=50 solo
# limita cuánto dura el intento una vez el estudiante lo inicia.

BANKS = [
    ("Integrales impropias — Parcial 2", INTEGRALES_PROBLEMS),
    ("P.V.I./P.V.F. — Parcial 2", PVI_PROBLEMS),
    ("EDP parabólica — Parcial 2", EDP_PROBLEMS),
]

SESSION_TITLES = [
    ("Parcial Práctico Dos - Sesión 1 (10:00-10:50)", 0),
    ("Parcial Práctico Dos - Sesión 2 (11:00-11:50)", 1),
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.Exam).filter_by(title=SESSION_TITLES[0][0]).first():
            print("'Parcial Práctico Dos' ya existía; no se modificó.")
            return

        bank_problems = []  # lista de listas de models.Problem, una por banco
        for bank_title, factories in BANKS:
            bank = db.query(models.ProblemBank).filter_by(title=bank_title).first()
            if not bank:
                bank = models.ProblemBank(
                    title=bank_title,
                    description=f"Variantes de {bank_title} para Parcial Práctico Dos.",
                    group=1,
                )
                db.add(bank)
                db.commit()
                db.refresh(bank)

            problems = []
            for factory in factories:
                data = factory()
                problem = models.Problem(
                    bank_id=bank.id,
                    title=data["title"],
                    statement_md=data["statement_md"],
                    starter_code=data["starter_code"],
                    rubric=json.dumps(data["rubric"]),
                    solution_code=data.get("solution_code"),
                )
                db.add(problem)
                problems.append(problem)
            db.commit()
            bank_problems.append(problems)
            print(f"Banco '{bank_title}' creado con {len(problems)} problema(s).")

        for exam_title, variant_index in SESSION_TITLES:
            exam = models.Exam(
                title=exam_title,
                description="Parcial Práctico Dos — integrales impropias, P.V.I./P.V.F. y EDP parabólica.",
                duration_minutes=50,
                is_open=False,  # el docente lo habilita desde su dashboard a la hora de cada sesión
                group=1,
            )
            db.add(exam)
            db.commit()
            db.refresh(exam)

            for order, problems in enumerate(bank_problems, start=1):
                problem = problems[variant_index]
                db.add(models.ExamProblem(exam_id=exam.id, problem_id=problem.id, order=order))
            db.commit()
            print(f"Examen '{exam_title}' creado con {len(bank_problems)} problema(s).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
