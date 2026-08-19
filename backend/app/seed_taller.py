"""Siembra el examen "Simulacro Parcial Final" a partir de Taller_final.pdf,
usando las rutinas propias del curso en Rutinas_MN_Python_Est/.

Uso: python -m app.seed_taller
"""
import json

from .database import SessionLocal, engine, Base
from . import models

TP = lambda *vals: [[v] for v in vals]  # test_points de una sola variable


def problem1():
    statement = r"""
## Problema 1 — Trabajo (integración: Trapecio y Simpson 1/3)

El trabajo ejercido sobre un objeto es igual a la fuerza por la distancia recorrida
en la dirección de la fuerza. La velocidad de un objeto en dirección de la fuerza
está dada por

$$
v(t) = \frac{t}{e^{\cos(t/5)}}, \qquad t \in [0, 12]
$$

donde $v$ está en m/s. Emplee la regla de integración del **Trapecio** y de
**Simpson 1/3** con **140 subintervalos** para determinar el trabajo de este
objeto si se aplica una fuerza constante de 0.02 N.

### Instrucciones

1. Defina $v(t)$ como una función de Python.
2. Calcule la integral de $v$ en $[0,12]$ con `trapecio(v, 0, 12, 140)` **y** con
   `simpson(v, 0, 12, 140)` (`from trapecio import trapecio`, `from simpson import simpson`).
3. Multiplique cada integral por la fuerza (0.02 N) y guarde los resultados en
   **`W_trapecio`** y **`W_simpson`** (ya declaradas; no cambie sus nombres).

### Calificación (100 puntos)
- 20 pts — definir correctamente $v(t)$.
- 20 pts — llamar correctamente `trapecio(v, 0, 12, 140)`.
- 20 pts — valor final de `W_trapecio` correcto.
- 20 pts — llamar correctamente `simpson(v, 0, 12, 140)`.
- 20 pts — valor final de `W_simpson` correcto.
"""
    starter = (
        "W_trapecio = None  # No modificar el nombre de esta variable\n"
        "W_simpson = None   # No modificar el nombre de esta variable\n"
    )
    tp = TP(0.5, 1.5, 3.0, 5.0, 6.0, 8.0, 10.0, 11.5)
    rubric = [
        {"id": "def_v", "type": "function", "label": "Definir correctamente v(t)",
         "arg_names": ["t"], "ref_body": "t / np.exp(np.cos(t/5))", "test_points": tp, "points": 20},
        {"id": "call_trap", "type": "call", "label": "Llamar trapecio(v, 0, 12, 140) correctamente",
         "qualnames": ["trapecio.trapecio"], "strict": True,
         "match_args": [{"position": 0, "name": "f", "ref": "def_v"},
                         {"position": 1, "name": "a", "expected": 0},
                         {"position": 2, "name": "b", "expected": 12},
                         {"position": 3, "name": "M", "expected": 140}],
         "points": 20},
        {"id": "final_trap", "type": "final_value", "label": "Valor final de W_trapecio correcto",
         "variable": "W_trapecio", "expected": 1.6820188737458803, "tolerance": 1e-2, "points": 20},
        {"id": "call_simp", "type": "call", "label": "Llamar simpson(v, 0, 12, 140) correctamente",
         "qualnames": ["simpson.simpson"], "strict": True,
         "match_args": [{"position": 0, "name": "f", "ref": "def_v"},
                         {"position": 1, "name": "a", "expected": 0},
                         {"position": 2, "name": "b", "expected": 12},
                         {"position": 3, "name": "M", "expected": 140}],
         "points": 20},
        {"id": "final_simp", "type": "final_value", "label": "Valor final de W_simpson correcto",
         "variable": "W_simpson", "expected": 1.6819562802640533, "tolerance": 1e-2, "points": 20},
    ]
    solution = '''import numpy as np
from trapecio import trapecio
from simpson import simpson

def v(t):
    return t / np.exp(np.cos(t / 5))

W_trapecio = trapecio(v, 0, 12, 140) * 0.02
W_simpson = simpson(v, 0, 12, 140) * 0.02
'''
    return dict(
        title="Trabajo (Trapecio y Simpson)", statement_md=statement, starter_code=starter,
        rubric=rubric, solution_code=solution,
    )


def problem2():
    statement = r"""
## Problema 2 — Cuadratura de Gauss-Legendre (5 y 6 nodos)

Aproximar la integral

$$
\int_{-2}^{1} \frac{e^{x^2}}{\ln(12 - \sin^2(x))}\, dx
$$

empleando la fórmula de cuadratura Gaussiana con **5** y **6** nodos.

### Instrucciones

1. Defina el integrando como una función de Python.
2. Utilice `from CuadGaussLegendre import CuadGaussLegendre` y llame
   `CuadGaussLegendre(f, -2, 1, 5)` y `CuadGaussLegendre(f, -2, 1, 6)`.
3. Guarde los dos valores de la integral en **`I_N5`** e **`I_N6`** (ya declaradas).

### Calificación (100 puntos)
- 20 pts — definir correctamente el integrando.
- 20 pts — llamar correctamente con N=5.
- 20 pts — valor final de `I_N5` correcto.
- 20 pts — llamar correctamente con N=6.
- 20 pts — valor final de `I_N6` correcto.
"""
    starter = (
        "I_N5 = None  # No modificar el nombre de esta variable\n"
        "I_N6 = None  # No modificar el nombre de esta variable\n"
    )
    tp = TP(-1.9, -1.5, -1.0, -0.5, 0.0, 0.5, 0.9)
    rubric = [
        {"id": "def_f", "type": "function", "label": "Definir correctamente el integrando",
         "arg_names": ["x"], "ref_body": "np.exp(x**2) / np.log(12 - np.sin(x)**2)",
         "test_points": tp, "points": 20},
        {"id": "call_n5", "type": "call", "label": "Llamar CuadGaussLegendre(f, -2, 1, 5) correctamente",
         "qualnames": ["CuadGaussLegendre.CuadGaussLegendre"], "strict": True,
         "match_args": [{"position": 0, "name": "f", "ref": "def_f"},
                         {"position": 1, "name": "a", "expected": -2},
                         {"position": 2, "name": "b", "expected": 1},
                         {"position": 3, "name": "N", "expected": 5}],
         "points": 20},
        {"id": "final_n5", "type": "final_value", "label": "Valor final de I_N5 correcto",
         "variable": "I_N5", "expected": 7.406182469946832, "tolerance": 1e-3, "points": 20},
        {"id": "call_n6", "type": "call", "label": "Llamar CuadGaussLegendre(f, -2, 1, 6) correctamente",
         "qualnames": ["CuadGaussLegendre.CuadGaussLegendre"], "strict": True,
         "match_args": [{"position": 0, "name": "f", "ref": "def_f"},
                         {"position": 1, "name": "a", "expected": -2},
                         {"position": 2, "name": "b", "expected": 1},
                         {"position": 3, "name": "N", "expected": 6}],
         "points": 20},
        {"id": "final_n6", "type": "final_value", "label": "Valor final de I_N6 correcto",
         "variable": "I_N6", "expected": 7.422039771403417, "tolerance": 1e-3, "points": 20},
    ]
    solution = '''import numpy as np
from CuadGaussLegendre import CuadGaussLegendre

def f(x):
    return np.exp(x**2) / np.log(12 - np.sin(x)**2)

I_N5 = CuadGaussLegendre(f, -2, 1, 5)[0]
I_N6 = CuadGaussLegendre(f, -2, 1, 6)[0]
'''
    return dict(
        title="Cuadratura de Gauss-Legendre", statement_md=statement, starter_code=starter,
        rubric=rubric, solution_code=solution,
    )


def problem3():
    statement = r"""
## Problema 3 — Integral con singularidad removible (Simpson compuesta)

Aproximar el valor de

$$
\int_0^5 \frac{\cos(x)\tan^{-1}(5x)}{\sqrt{x}}\, dx
$$

empleando la fórmula compuesta de **Simpson 1/3** con $m=30$ subintervalos.

**Cuidado:** el integrando no está definido en $x=0$ tal como está escrito
($0/0$), pero su límite cuando $x \to 0^+$ sí existe (es 0). Su función de
Python debe manejar ese caso especial para poder evaluarse en $x=0$.

### Instrucciones

1. Defina el integrando (con el caso especial en $x=0$) como una función de Python.
2. Utilice `from simpson import simpson` y llame `simpson(f, 0, 5, 30)`.
3. Guarde el resultado en **`I`** (ya declarada).

### Calificación (100 puntos)
- 30 pts — definir correctamente el integrando (incluyendo el caso $x=0$).
- 30 pts — llamar correctamente `simpson(f, 0, 5, 30)`.
- 40 pts — valor final de `I` correcto.
"""
    starter = "I = None  # No modificar el nombre de esta variable\n"
    tp = [[0.0], [0.2], [0.8], [1.5], [2.5], [3.5], [4.5], [4.9]]
    rubric = [
        {"id": "def_f", "type": "function", "label": "Definir correctamente el integrando (incl. x=0)",
         "arg_names": ["x"],
         "ref_body": "0.0 if x < 1e-12 else np.cos(x)*np.arctan(5*x)/np.sqrt(x)",
         "test_points": tp, "points": 30},
        {"id": "call_correct", "type": "call", "label": "Llamar simpson(f, 0, 5, 30) correctamente",
         "qualnames": ["simpson.simpson"], "strict": True,
         "match_args": [{"position": 0, "name": "f", "ref": "def_f"},
                         {"position": 1, "name": "a", "expected": 0},
                         {"position": 2, "name": "b", "expected": 5},
                         {"position": 3, "name": "M", "expected": 30}],
         "points": 30},
        {"id": "final", "type": "final_value", "label": "Valor final de I correcto",
         "variable": "I", "expected": -0.20950687632234266, "tolerance": 1e-2, "points": 40},
    ]
    solution = '''import numpy as np
from simpson import simpson

def f(x):
    if x < 1e-12:
        return 0.0
    return np.cos(x) * np.arctan(5 * x) / np.sqrt(x)

I = simpson(f, 0, 5, 30)
'''
    return dict(
        title="Integral con singularidad removible", statement_md=statement, starter_code=starter,
        rubric=rubric, solution_code=solution,
    )


def problem5():
    statement = r"""
## Problema 5 — Método de Euler

La tasa de cambio de temperatura $u$ de un cuerpo que está perdiendo calor por
convección natural, con exteriores a temperatura constante, viene dada por:

$$
u'(t) = -\frac{27}{100}\big(60 - u(t)\big)^{5/4}
$$

Se sabe que $u(1) = 48°C$. Use el **método de Euler** con $h=0.25$ para
aproximar la temperatura del cuerpo cuando $t=3.25$.

### Instrucciones

1. Defina $f(t,u)$ como una función de Python.
2. Utilice `from Euler import Euler` y llame `Euler(f, 1, 3.25, 48, 9)` (M=9 pasos, ya que $h=(3.25-1)/9=0.25$).
3. Guarde $u(3.25)$ en **`u_325`** (ya declarada).

### Calificación (100 puntos)
- 25 pts — definir correctamente $f(t,u)$.
- 25 pts — llamar correctamente `Euler(f, 1, 3.25, 48, 9)`.
- 50 pts — valor final de `u_325` correcto.
"""
    starter = "u_325 = None  # No modificar el nombre de esta variable\n"
    tp = [[1.0, 48.0], [1.5, 50.0], [2.0, 52.0], [2.5, 55.0], [3.0, 58.0], [3.25, 59.0]]
    rubric = [
        {"id": "def_f", "type": "function", "label": "Definir correctamente f(t,u)",
         "arg_names": ["t", "u"], "ref_body": "-0.27*(60-u)**1.25", "test_points": tp, "points": 25},
        {"id": "call_correct", "type": "call", "label": "Llamar Euler(f, 1, 3.25, 48, 9) correctamente",
         "qualnames": ["Euler.Euler"], "strict": True,
         "match_args": [{"position": 0, "name": "f", "ref": "def_f"},
                         {"position": 1, "name": "a", "expected": 1},
                         {"position": 2, "name": "b", "expected": 3.25},
                         {"position": 3, "name": "ya", "expected": 48},
                         {"position": 4, "name": "M", "expected": 9}],
         "points": 25},
        {"id": "final", "type": "final_value", "label": "Valor final de u_325 correcto",
         "variable": "u_325", "expected": 20.0188213841841, "tolerance": 1e-2, "points": 50},
    ]
    solution = '''from Euler import Euler

def f(t, u):
    return -0.27 * (60 - u) ** 1.25

u_325 = Euler(f, 1, 3.25, 48, 9)[-1, 1]
'''
    return dict(
        title="Método de Euler", statement_md=statement, starter_code=starter,
        rubric=rubric, solution_code=solution,
    )


def problem6():
    statement = r"""
## Problema 6 — Euler modificado, Heun y Runge-Kutta 4

Considere el P.V.I.

$$
10y' = -5y\ln(t^2+1), \qquad 2 \le t \le 4, \qquad y(2) = 1
$$

Aproximar la solución con tamaño de paso $h=0.4$ empleando los métodos de
**Euler modificado**, **Heun** y **Runge-Kutta clásico de orden 4**.

### Instrucciones

1. Defina $f(t,y) = -0.5\,y\ln(t^2+1)$ (equivalente a despejar $y'$ de la ecuación).
2. Llame, con M=5 pasos ($h=(4-2)/5=0.4$):
   - `from RK2_EulerMod import RK2_EulerMod` → `RK2_EulerMod(f, 2, 4, 1, 5)`
   - `from RK3_Heun import RK3_Heun` → `RK3_Heun(f, 2, 4, 1, 5)`
   - `from RK4 import RK4` → `RK4(f, 2, 4, 1, 5)`
3. Guarde $y(4)$ de cada método en **`y_eulermod`**, **`y_heun`**, **`y_rk4`** (ya declaradas).

### Calificación (100 puntos)
- 10 pts — definir correctamente f(t,y).
- Por cada método (30 pts c/u): 10 pts llamada correcta + 20 pts valor final correcto.
"""
    starter = (
        "y_eulermod = None  # No modificar el nombre de esta variable\n"
        "y_heun = None       # No modificar el nombre de esta variable\n"
        "y_rk4 = None        # No modificar el nombre de esta variable\n"
    )
    tp = [[2.0, 1.0], [2.4, 0.8], [2.8, 0.6], [3.2, 0.5], [3.6, 0.4], [4.0, 0.3]]

    def method_checks(prefix, qualname, expected):
        return [
            {"id": f"call_{prefix}", "type": "call", "label": f"Llamar {qualname.split('.')[-1]}(f, 2, 4, 1, 5) correctamente",
             "qualnames": [qualname], "strict": True,
             "match_args": [{"position": 0, "name": "f", "ref": "def_f"},
                             {"position": 1, "name": "a", "expected": 2},
                             {"position": 2, "name": "b", "expected": 4},
                             {"position": 3, "name": "ya", "expected": 1},
                             {"position": 4, "name": "M", "expected": 5}],
             "points": 10},
            {"id": f"final_{prefix}", "type": "final_value", "label": f"Valor final de y_{prefix} correcto",
             "variable": f"y_{prefix}", "expected": expected, "tolerance": 1e-2, "points": 20},
        ]

    rubric = [
        {"id": "def_f", "type": "function", "label": "Definir correctamente f(t,y)",
         "arg_names": ["t", "y"], "ref_body": "-0.5*y*np.log(t**2+1)", "test_points": tp, "points": 10},
    ]
    rubric += method_checks("eulermod", "RK2_EulerMod.RK2_EulerMod", 0.11572047307988566)
    rubric += method_checks("heun", "RK3_Heun.RK3_Heun", 0.10189251524348174)
    rubric += method_checks("rk4", "RK4.RK4", 0.10288004845253458)

    solution = '''import numpy as np
from RK2_EulerMod import RK2_EulerMod
from RK3_Heun import RK3_Heun
from RK4 import RK4

def f(t, y):
    return -0.5 * y * np.log(t**2 + 1)

y_eulermod = RK2_EulerMod(f, 2, 4, 1, 5)[-1, 1]
y_heun = RK3_Heun(f, 2, 4, 1, 5)[-1, 1]
y_rk4 = RK4(f, 2, 4, 1, 5)[-1, 1]
'''
    return dict(
        title="Euler modificado, Heun y RK4", statement_md=statement, starter_code=starter,
        rubric=rubric, solution_code=solution,
    )


def problem7():
    statement = r"""
## Problema 7 — P.V.I. de orden superior (sistema con RK4)

Considere el P.V.I. de orden superior:

$$
\begin{cases}
y''(t) - \cos(z(t)) = \ln(t^2+1), & 1 \le t \le 4,\\
z'(t) + \tan^{-1}(y(t)) = \sin(y'(t)) - 4, & 1 \le t \le 4,\\
y(1)=1,\quad y'(1)=-1,\quad z(1)=1.
\end{cases}
$$

Aproximar la solución empleando **Runge-Kutta de orden 4** con $h=0.3$.

### Instrucciones

1. Escriba el sistema como de primer orden con el vector de estado
   $U = [y, y', z]$, de modo que $U' = [\,y',\; \cos(z)+\ln(t^2+1),\;
   \sin(y')-4-\tan^{-1}(y)\,]$. Defina `F(t, U)` que retorne esa lista.
2. Utilice `from RK4_sist import RK4_sist` y llame
   `RK4_sist(F, 1, 4, [1,-1,1], 10)` (M=10, ya que $h=(4-1)/10=0.3$).
3. Guarde $y(4)$ (primera componente en el último paso) en **`y4`** (ya declarada).

### Calificación (100 puntos)
- 30 pts — definir correctamente `F(t, U)`.
- 30 pts — llamar correctamente `RK4_sist(F, 1, 4, [1,-1,1], 10)`.
- 40 pts — valor final de `y4` correcto.
"""
    starter = "y4 = None  # No modificar el nombre de esta variable\n"
    tp = [
        [1.0, [1.0, -1.0, 1.0]],
        [2.0, [0.5, 0.5, -1.0]],
        [3.0, [2.0, -0.5, 0.5]],
        [4.0, [-1.0, 1.5, 2.0]],
    ]
    rubric = [
        {"id": "def_F", "type": "function", "label": "Definir correctamente F(t, U)",
         "arg_names": ["t", "U"],
         "ref_body": "[U[1], np.cos(U[2]) + np.log(t**2+1), np.sin(U[1]) - 4 - np.arctan(U[0])]",
         "test_points": tp, "points": 30},
        {"id": "call_correct", "type": "call", "label": "Llamar RK4_sist(F, 1, 4, [1,-1,1], 10) correctamente",
         "qualnames": ["RK4_sist.RK4_sist"], "strict": True,
         "match_args": [{"position": 0, "name": "F", "ref": "def_F"},
                         {"position": 1, "name": "a", "expected": 1},
                         {"position": 2, "name": "b", "expected": 4},
                         {"position": 3, "name": "Za", "expected": [1, -1, 1]},
                         {"position": 4, "name": "M", "expected": 10}],
         "points": 30},
        {"id": "final", "type": "final_value", "label": "Valor final de y4 correcto",
         "variable": "y4", "expected": 5.5069678873563594, "tolerance": 1e-2, "points": 40},
    ]
    solution = '''import numpy as np
from RK4_sist import RK4_sist

def F(t, U):
    return [U[1], np.cos(U[2]) + np.log(t**2 + 1), np.sin(U[1]) - 4 - np.arctan(U[0])]

T, Z = RK4_sist(F, 1, 4, [1, -1, 1], 10)
y4 = Z[-1, 0]
'''
    return dict(
        title="P.V.I. de orden superior (RK4 sistema)", statement_md=statement, starter_code=starter,
        rubric=rubric, solution_code=solution,
    )


def problem8():
    statement = r"""
## Problema 8 — P.V.F. lineal (diferencias finitas)

Aproximar la solución del siguiente P.V.F. usando el método de diferencias
finitas con tamaño de paso $h=0.2$:

$$
\begin{cases}
e^{-x}y''(x) + \dfrac{4}{3+x^2}y'(x) - 3(x+1)^2y(x) = \ln(81-x^2), & \tfrac12 \le x \le \tfrac32,\\
y(\tfrac12)=5, \quad y(\tfrac32)=-3.
\end{cases}
$$

### Instrucciones

1. Reescriba la ecuación en la forma estándar $y'' = p(x)y' + q(x)y + r(x)$
   (dividiendo por $e^{-x}$) y defina `p`, `q`, `r` como funciones de Python:

$$
p(x) = -\frac{4e^{x}}{3+x^2}, \qquad q(x) = 3(x+1)^2 e^{x}, \qquad r(x) = e^{x}\ln(81-x^2)
$$

2. Utilice `from Diffin_PVF import Diffin_PVF` y llame
   `Diffin_PVF(p, q, r, 0.5, 1.5, 5, -3, 5)` (N=5, ya que $h=(1.5-0.5)/5=0.2$).
3. La rutina retorna una tabla `[T, X]`; guarde en **`y_09`** el valor de $y(0.9)$
   (tercera fila de la tabla, columna de la solución).

### Calificación (100 puntos)
- 15 pts c/u — definir correctamente p(x), q(x), r(x) (45 pts).
- 25 pts — llamar correctamente `Diffin_PVF(p, q, r, 0.5, 1.5, 5, -3, 5)`.
- 30 pts — valor final de `y_09` correcto.
"""
    starter = "y_09 = None  # No modificar el nombre de esta variable\n"
    tp = [[0.6], [0.8], [1.0], [1.2], [1.4]]
    rubric = [
        {"id": "def_p", "type": "function", "label": "Definir correctamente p(x)",
         "arg_names": ["x"], "ref_body": "-4*np.exp(x)/(3+x**2)", "test_points": tp, "points": 15},
        {"id": "def_q", "type": "function", "label": "Definir correctamente q(x)",
         "arg_names": ["x"], "ref_body": "3*(x+1)**2*np.exp(x)", "test_points": tp, "points": 15},
        {"id": "def_r", "type": "function", "label": "Definir correctamente r(x)",
         "arg_names": ["x"], "ref_body": "np.exp(x)*np.log(81-x**2)", "test_points": tp, "points": 15},
        {"id": "call_correct", "type": "call", "label": "Llamar Diffin_PVF(p, q, r, 0.5, 1.5, 5, -3, 5) correctamente",
         "qualnames": ["Diffin_PVF.Diffin_PVF"], "strict": True,
         "match_args": [{"position": 0, "name": "p", "ref": "def_p"},
                         {"position": 1, "name": "q", "ref": "def_q"},
                         {"position": 2, "name": "r", "ref": "def_r"},
                         {"position": 3, "name": "a", "expected": 0.5},
                         {"position": 4, "name": "b", "expected": 1.5},
                         {"position": 5, "name": "alpha", "expected": 5},
                         {"position": 6, "name": "beta", "expected": -3},
                         {"position": 7, "name": "N", "expected": 5}],
         "points": 25},
        {"id": "final", "type": "final_value", "label": "Valor final de y_09 correcto",
         "variable": "y_09", "expected": -0.06998583999696027, "tolerance": 1e-2, "points": 30},
    ]
    solution = '''import numpy as np
from Diffin_PVF import Diffin_PVF

def p(x):
    return -4 * np.exp(x) / (3 + x**2)

def q(x):
    return 3 * (x + 1)**2 * np.exp(x)

def r(x):
    return np.exp(x) * np.log(81 - x**2)

F = Diffin_PVF(p, q, r, 0.5, 1.5, 5, -3, 5)
y_09 = F[2, 1]
'''
    return dict(
        title="P.V.F. lineal (diferencias finitas)", statement_md=statement, starter_code=starter,
        rubric=rubric, solution_code=solution,
    )


def problem9():
    statement = r"""
## Problema 9 — P.V.F. por el método de disparo

Aproximar la solución del P.V.F.

$$
\begin{cases}
y'' = \cot(t)\,y' + e^{-t^2}y + \ln(t^2), & 1 \le t \le 2,\\
y(1) = 1.5, \quad y(2) = -2,
\end{cases}
$$

empleando el **método de disparo** con $h=0.1$.

### Instrucciones

1. Escriba los dos sistemas de primer orden que exige `DisparoLin`, con estado
   $U=[y,y']$:
   - `F1(t, U)` para el problema **no homogéneo**: `[U[1], cot(t)*U[1] + exp(-t**2)*U[0] + log(t**2)]`
   - `F2(t, U)` para el problema **homogéneo** (sin el término $\ln(t^2)$): `[U[1], cot(t)*U[1] + exp(-t**2)*U[0]]`
2. Utilice `from DisparoLin import DisparoLin` y llame
   `DisparoLin(F1, F2, 1, 2, 1.5, -2, 10)` (M=10, ya que $h=(2-1)/10=0.1$).
3. La rutina retorna una tabla `[T, X]`; guarde en **`y_15`** el valor de $y(1.5)$
   (fila correspondiente a $t=1.5$).

### Calificación (100 puntos)
- 20 pts — definir correctamente `F1`.
- 20 pts — definir correctamente `F2`.
- 20 pts — llamar correctamente `DisparoLin(F1, F2, 1, 2, 1.5, -2, 10)`.
- 40 pts — valor final de `y_15` correcto.
"""
    starter = "y_15 = None  # No modificar el nombre de esta variable\n"
    tp = [
        [1.2, [0.5, -0.3]],
        [1.5, [1.0, 0.2]],
        [1.8, [-0.5, 0.8]],
    ]
    rubric = [
        {"id": "def_F1", "type": "function", "label": "Definir correctamente F1(t, U) (no homogéneo)",
         "arg_names": ["t", "U"],
         "ref_body": "[U[1], (1/np.tan(t))*U[1] + np.exp(-t**2)*U[0] + np.log(t**2)]",
         "test_points": tp, "points": 20},
        {"id": "def_F2", "type": "function", "label": "Definir correctamente F2(t, U) (homogéneo)",
         "arg_names": ["t", "U"],
         "ref_body": "[U[1], (1/np.tan(t))*U[1] + np.exp(-t**2)*U[0]]",
         "test_points": tp, "points": 20},
        {"id": "call_correct", "type": "call", "label": "Llamar DisparoLin(F1, F2, 1, 2, 1.5, -2, 10) correctamente",
         "qualnames": ["DisparoLin.DisparoLin"], "strict": True,
         "match_args": [{"position": 0, "name": "F1", "ref": "def_F1"},
                         {"position": 1, "name": "F2", "ref": "def_F2"},
                         {"position": 2, "name": "a", "expected": 1},
                         {"position": 3, "name": "b", "expected": 2},
                         {"position": 4, "name": "alpha", "expected": 1.5},
                         {"position": 5, "name": "beta", "expected": -2},
                         {"position": 6, "name": "M", "expected": 10}],
         "points": 20},
        {"id": "final", "type": "final_value", "label": "Valor final de y_15 correcto",
         "variable": "y_15", "expected": -0.3146240474067632, "tolerance": 1e-2, "points": 40},
    ]
    solution = '''import numpy as np
from DisparoLin import DisparoLin

def F1(t, U):
    return [U[1], (1 / np.tan(t)) * U[1] + np.exp(-t**2) * U[0] + np.log(t**2)]

def F2(t, U):
    return [U[1], (1 / np.tan(t)) * U[1] + np.exp(-t**2) * U[0]]

L = DisparoLin(F1, F2, 1, 2, 1.5, -2, 10)
y_15 = L[5, 1]
'''
    return dict(
        title="P.V.F. por el método de disparo", statement_md=statement, starter_code=starter,
        rubric=rubric, solution_code=solution,
    )


def problem10():
    statement = r"""
## Problema 10 — Problema elíptico (Poisson, diferencias finitas)

Aproximar la solución del problema elíptico

$$
\begin{cases}
u_{xx}(x,y) + u_{yy}(x,y) = 6(x+y), & 1<x<2,\ 2<y<4,\\
u(1,y)=y^3+1, & 2\le y \le 4,\\
u(2,y)=y^3+8, & 2\le y \le 4,\\
u(x,2)=x^3+8, & 1\le x \le 2,\\
u(x,4)=x^3+64, & 1\le x \le 2,
\end{cases}
$$

por el método de diferencias finitas tomando $h=\tfrac13$ y $k=\tfrac12$.

### Instrucciones

1. Defina `g(x,y)`, y las 4 condiciones de frontera como funciones de Python:
   `f1` (abajo, $y=2$), `f2` (derecha, $x=2$), `f3` (arriba, $y=4$), `f4` (izquierda, $x=1$).
2. Utilice `from Poisson import Poisson` y llame
   `Poisson(g, f1, f2, f3, f4, 1, 2, 2, 4, 4, 5)` (m=4 puntos en x, n=5 puntos en y).
   Esto retorna una matriz `U` de tamaño (n, m) = (5, 4), donde `U[j, i]`
   corresponde al punto $(x_i, y_j)$ con $x = [1,\ 4/3,\ 5/3,\ 2]$ (i=0..3) y
   $y = [2,\ 2.5,\ 3,\ 3.5,\ 4]$ (j=0..4).
3. Guarde en **`u_val`** el valor de la solución aproximada en $x=4/3,\ y=3$,
   es decir, **`u_val = U[2, 1]`**.

### Calificación (100 puntos)
- 10 pts c/u — definir correctamente g, f1, f2, f3, f4 (50 pts).
- 20 pts — llamar correctamente `Poisson(g, f1, f2, f3, f4, 1, 2, 2, 4, 4, 5)`.
- 30 pts — valor final de `u_val` correcto.
"""
    starter = "u_val = None  # No modificar el nombre de esta variable\n"
    tp_xy = [[1.2, 2.3], [1.5, 3.0], [1.8, 3.7]]
    tp_x = [[1.1], [1.4], [1.7], [2.0]]
    tp_y = [[2.2], [2.8], [3.4], [4.0]]
    rubric = [
        {"id": "def_g", "type": "function", "label": "Definir correctamente g(x,y)",
         "arg_names": ["x", "y"], "ref_body": "6*(x+y)", "test_points": tp_xy, "points": 10},
        {"id": "def_f1", "type": "function", "label": "Definir correctamente f1 (abajo, y=2)",
         "arg_names": ["x"], "ref_body": "x**3+8", "test_points": tp_x, "points": 10},
        {"id": "def_f2", "type": "function", "label": "Definir correctamente f2 (derecha, x=2)",
         "arg_names": ["y"], "ref_body": "y**3+8", "test_points": tp_y, "points": 10},
        {"id": "def_f3", "type": "function", "label": "Definir correctamente f3 (arriba, y=4)",
         "arg_names": ["x"], "ref_body": "x**3+64", "test_points": tp_x, "points": 10},
        {"id": "def_f4", "type": "function", "label": "Definir correctamente f4 (izquierda, x=1)",
         "arg_names": ["y"], "ref_body": "y**3+1", "test_points": tp_y, "points": 10},
        {"id": "call_correct", "type": "call",
         "label": "Llamar Poisson(g, f1, f2, f3, f4, 1, 2, 2, 4, 4, 5) correctamente",
         "qualnames": ["Poisson.Poisson"], "strict": True,
         "match_args": [{"position": 0, "name": "g", "ref": "def_g"},
                         {"position": 1, "name": "f1", "ref": "def_f1"},
                         {"position": 2, "name": "f2", "ref": "def_f2"},
                         {"position": 3, "name": "f3", "ref": "def_f3"},
                         {"position": 4, "name": "f4", "ref": "def_f4"},
                         {"position": 5, "name": "a", "expected": 1},
                         {"position": 6, "name": "b", "expected": 2},
                         {"position": 7, "name": "c", "expected": 2},
                         {"position": 8, "name": "d", "expected": 4},
                         {"position": 9, "name": "m", "expected": 4},
                         {"position": 10, "name": "n", "expected": 5}],
         "points": 20},
        {"id": "final", "type": "final_value", "label": "Valor final de u_val correcto",
         "variable": "u_val", "expected": 29.37037037037037, "tolerance": 1e-2, "points": 30},
    ]
    solution = '''from Poisson import Poisson

def g(x, y):
    return 6 * (x + y)

def f1(x):
    return x**3 + 8

def f2(y):
    return y**3 + 8

def f3(x):
    return x**3 + 64

def f4(y):
    return y**3 + 1

U = Poisson(g, f1, f2, f3, f4, 1, 2, 2, 4, 4, 5)
u_val = U[2, 1]
'''
    return dict(
        title="Problema elíptico (Poisson)", statement_md=statement, starter_code=starter,
        rubric=rubric, solution_code=solution,
    )


def problem11():
    statement = r"""
## Problema 11 — Problema parabólico (ecuación del calor)

Considere el problema parabólico:

$$
\frac{\partial u}{\partial t} = 2\frac{\partial^2 u}{\partial x^2}, \quad x\in(0,1),\ t>0
$$
$$
u(x,0)=x(1-x), \qquad u(0,t)=\cos(t), \qquad u(1,t)=\sin(t)
$$

**(a)** Estime el máximo valor $k$ que se debe tomar si $h=1/10$ para que el
esquema adelante en tiempo (progresivo) sea estable.

**(b)** Con esos $h,k$ aproxime la solución con el esquema **adelante en
tiempo** y dé un valor aproximado para $u(x_3,t_2)$.

**(d)** Con esos $h,k$ aproxime la solución con el esquema de **Crank-Nicolson**
y dé un valor aproximado para $u(x_3,t_2)$.

(La parte (c), esquema totalmente implícito "atrás en tiempo", no se califica
en la plataforma por no haber una rutina de curso disponible para ese esquema —
resuélvala en papel si su docente lo solicita.)

**Convención de índices:** $x_i = i\cdot h$, $t_j = j \cdot k$, ambos empezando en 0
(es decir, $x_3=0.3$ y $t_2$ es el segundo paso de tiempo).

### Instrucciones

1. Guarde el valor máximo de $k$ (con $c^2=2$, la estabilidad exige
   $r = c^2 k/h^2 \le 1/2$) en **`k_max`**.
2. Defina $u(x,0)$, $u(0,t)$, $u(1,t)$ como funciones de Python.
3. Utilice `from DifAdelante import DifAdelante` y `from CrankNicolson import CrankNicolson`,
   llamando ambas con `f, g1, g2, a=1, b=2*k_max, c=sqrt(2), n=11, m=3`
   (con `n=11` nodos espaciales y `m=3` pasos de tiempo, suficientes para llegar a $t_2$).
4. Guarde $u(x_3,t_2)$ de cada esquema en **`u32_adelante`** y **`u32_cn`**.

### Calificación (100 puntos)
- 10 pts — valor de `k_max` correcto.
- 10 pts — definir correctamente la condición inicial $u(x,0)$.
- 10 pts — definir correctamente $u(0,t)=\cos(t)$.
- 10 pts — definir correctamente $u(1,t)=\sin(t)$.
- 15 pts — llamar correctamente `DifAdelante`.
- 15 pts — valor final de `u32_adelante` correcto.
- 15 pts — llamar correctamente `CrankNicolson`.
- 15 pts — valor final de `u32_cn` correcto.
"""
    starter = (
        "k_max = None        # No modificar el nombre de esta variable\n"
        "u32_adelante = None # No modificar el nombre de esta variable\n"
        "u32_cn = None       # No modificar el nombre de esta variable\n"
    )
    tp_ic = [[0.1], [0.3], [0.5], [0.7], [0.9]]
    tp_t = [[0.2], [0.6], [1.0], [1.5]]
    rubric = [
        {"id": "final_kmax", "type": "final_value", "label": "Valor de k_max correcto",
         "variable": "k_max", "expected": 0.0025, "tolerance": 1e-6, "points": 10},
        {"id": "def_ic", "type": "function", "label": "Definir correctamente u(x,0) = x(1-x)",
         "arg_names": ["x"], "ref_body": "x*(1-x)", "test_points": tp_ic, "points": 10},
        {"id": "def_g1", "type": "function", "label": "Definir correctamente u(0,t) = cos(t)",
         "arg_names": ["t"], "ref_body": "np.cos(t)", "test_points": tp_t, "points": 10},
        {"id": "def_g2", "type": "function", "label": "Definir correctamente u(1,t) = sin(t)",
         "arg_names": ["t"], "ref_body": "np.sin(t)", "test_points": tp_t, "points": 10},
        {"id": "call_adelante", "type": "call", "label": "Llamar DifAdelante correctamente",
         "qualnames": ["DifAdelante.DifAdelante"], "strict": True,
         "match_args": [{"position": 0, "name": "f", "ref": "def_ic"},
                         {"position": 1, "name": "g1", "ref": "def_g1"},
                         {"position": 2, "name": "g2", "ref": "def_g2"},
                         {"position": 3, "name": "a", "expected": 1},
                         {"position": 5, "name": "c", "expected": 1.4142135623730951},
                         {"position": 6, "name": "n", "expected": 11}],
         "points": 15},
        {"id": "final_adelante", "type": "final_value", "label": "Valor final de u32_adelante correcto",
         "variable": "u32_adelante", "expected": 0.19, "tolerance": 1e-2, "points": 15},
        {"id": "call_cn", "type": "call", "label": "Llamar CrankNicolson correctamente",
         "qualnames": ["CrankNicolson.CrankNicolson"], "strict": True,
         "match_args": [{"position": 0, "name": "f", "ref": "def_ic"},
                         {"position": 1, "name": "g1", "ref": "def_g1"},
                         {"position": 2, "name": "g2", "ref": "def_g2"},
                         {"position": 3, "name": "a", "expected": 1},
                         {"position": 5, "name": "c", "expected": 1.4142135623730951},
                         {"position": 6, "name": "n", "expected": 11}],
         "points": 15},
        {"id": "final_cn", "type": "final_value", "label": "Valor final de u32_cn correcto",
         "variable": "u32_cn", "expected": 0.23317186341249443, "tolerance": 1e-2, "points": 15},
    ]
    solution = '''import numpy as np
from DifAdelante import DifAdelante
from CrankNicolson import CrankNicolson

k_max = 0.0025

def f(x):
    return x * (1 - x)

def g1(t):
    return np.cos(t)

def g2(t):
    return np.sin(t)

U1 = DifAdelante(f, g1, g2, 1, 2 * k_max, 2**0.5, 11, 3)
u32_adelante = U1[2, 3]

U2 = CrankNicolson(f, g1, g2, 1, 2 * k_max, 2**0.5, 11, 3)
u32_cn = U2[2, 3]
'''
    return dict(
        title="Problema parabólico (calor)", statement_md=statement, starter_code=starter,
        rubric=rubric, solution_code=solution,
    )


def problem12():
    statement = r"""
## Problema 12 — Problema hiperbólico (ecuación de onda)

Considere el problema hiperbólico:

$$
u_{tt}(x,t) = u_{xx}(x,t), \quad 0<x<\tfrac{\pi}{2},\ t>0
$$
$$
u(0,t)=0, \qquad u\!\left(\tfrac{\pi}{2},t\right)=\cos\!\left(\tfrac{\pi}{4}+t\right)
$$
$$
u(x,0)=\tfrac{\sqrt2}{2}\sin(x), \qquad u_t(x,0)=-\tfrac{\sqrt2}{2}\sin(x)
$$

**(a)** Si $h=1/100$ estime el máximo valor $k$ para que el esquema en
diferencias finitas sea estable.

**(b)** Con esos $h,k$ aproxime la solución y determine $u(x_{50},t_{50})$.

**Convención de índices:** $x_i=i\cdot h$, $t_j=j\cdot k$, empezando en 0.
Use $n=158$ nodos espaciales (de modo que $x_{157}=\pi/2$ aproximadamente, ya
que $\pi/2$ no es múltiplo exacto de $h=0.01$) y al menos $m=51$ pasos de tiempo.

### Instrucciones

1. Guarde el valor máximo de $k$ (con $c=1$, la condición CFL exige
   $r = ck/h \le 1$) en **`k_max`**.
2. Defina $u(x,0)$, $u_t(x,0)$, $u(0,t)$, $u(\pi/2,t)$ como funciones de Python.
3. Utilice `from DifinHiper import DifinHiper` y llame con
   `f, g, q1, q2, a=pi/2, b=50*k_max, c=1, n=158, m=51`.
4. Guarde $u(x_{50},t_{50})$ en **`u5050`**.

### Calificación (100 puntos)
- 10 pts — valor de `k_max` correcto.
- 10 pts — definir correctamente $u(x,0)$.
- 10 pts — definir correctamente $u_t(x,0)$.
- 5 pts — definir correctamente $u(0,t)=0$.
- 15 pts — definir correctamente $u(\pi/2,t)=\cos(\pi/4+t)$.
- 20 pts — llamar correctamente `DifinHiper`.
- 30 pts — valor final de `u5050` correcto.
"""
    starter = (
        "k_max = None  # No modificar el nombre de esta variable\n"
        "u5050 = None  # No modificar el nombre de esta variable\n"
    )
    tp = [[0.1], [0.5], [1.0], [1.4]]
    tp_t = [[0.2], [0.6], [1.0], [1.5]]
    rubric = [
        {"id": "final_kmax", "type": "final_value", "label": "Valor de k_max correcto",
         "variable": "k_max", "expected": 0.01, "tolerance": 1e-6, "points": 10},
        {"id": "def_f", "type": "function", "label": "Definir correctamente u(x,0)",
         "arg_names": ["x"], "ref_body": "(2**0.5/2)*np.sin(x)", "test_points": tp, "points": 10},
        {"id": "def_g", "type": "function", "label": "Definir correctamente u_t(x,0)",
         "arg_names": ["x"], "ref_body": "-(2**0.5/2)*np.sin(x)", "test_points": tp, "points": 10},
        {"id": "def_q1", "type": "function", "label": "Definir correctamente u(0,t) = 0",
         "arg_names": ["t"], "ref_body": "0.0*t", "test_points": tp_t, "points": 5},
        {"id": "def_q2", "type": "function", "label": "Definir correctamente u(pi/2,t) = cos(pi/4+t)",
         "arg_names": ["t"], "ref_body": "np.cos(np.pi/4 + t)", "test_points": tp_t, "points": 15},
        {"id": "call_correct", "type": "call", "label": "Llamar DifinHiper correctamente",
         "qualnames": ["DifinHiper.DifinHiper"], "strict": True,
         "match_args": [{"position": 0, "name": "f", "ref": "def_f"},
                         {"position": 1, "name": "g", "ref": "def_g"},
                         {"position": 2, "name": "q1", "ref": "def_q1"},
                         {"position": 3, "name": "q2", "ref": "def_q2"},
                         {"position": 6, "name": "c", "expected": 1},
                         {"position": 7, "name": "n", "expected": 158}],
         "points": 20},
        {"id": "final", "type": "final_value", "label": "Valor final de u5050 correcto",
         "variable": "u5050", "expected": 0.13503718702343354, "tolerance": 5e-2, "points": 30},
    ]
    solution = '''import numpy as np
from DifinHiper import DifinHiper

k_max = 0.01

def f(x):
    return (2**0.5 / 2) * np.sin(x)

def g(x):
    return -(2**0.5 / 2) * np.sin(x)

def q1(t):
    return 0.0 * t

def q2(t):
    return np.cos(np.pi / 4 + t)

U = DifinHiper(f, g, q1, q2, np.pi / 2, 50 * k_max, 1, 158, 51)
u5050 = U[50, 50]
'''
    return dict(
        title="Problema hiperbólico (onda)", statement_md=statement, starter_code=starter,
        rubric=rubric, solution_code=solution,
    )


PROBLEMS = [problem1, problem2, problem3, problem5, problem6, problem7,
            problem8, problem9, problem10, problem11, problem12]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        exam = db.query(models.Exam).filter_by(title="Simulacro Parcial Final").first()
        if exam:
            print("El examen 'Simulacro Parcial Final' ya existía; no se modificó.")
            return

        bank = db.query(models.ProblemBank).filter_by(title="Simulacro Parcial Final").first()
        if not bank:
            bank = models.ProblemBank(
                title="Simulacro Parcial Final",
                description="Problemas de Taller_final.pdf — integración, EDOs, PVF y PDEs.",
                group=1,
            )
            db.add(bank)
            db.commit()
            db.refresh(bank)

        exam = models.Exam(
            title="Simulacro Parcial Final",
            description="Simulacro basado en Taller_final.pdf — integración, EDOs, PVF y PDEs.",
            duration_minutes=None,  # sin límite de tiempo: el estudiante puede entrar y salir libremente
            group=1,
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)

        for order, factory in enumerate(PROBLEMS, start=1):
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
            db.flush()
            db.add(models.ExamProblem(exam_id=exam.id, problem_id=problem.id, order=order))

        db.commit()
        print(f"Examen 'Simulacro Parcial Final' creado con {len(PROBLEMS)} problemas.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
