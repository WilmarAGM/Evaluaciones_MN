#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores:  Mauricio Osorio, a partir de la rutina existente en MATLAB y con
           la ayuda de una IA

CrankNicolson:

Resuelve la ecuacion del calor, u_{t} = c^2 u_{xx}  para x in [0,a]  y t en [0,b],
con el metodo de Crank Nicolson 

  
Parámetros:
- f = u (x, 0): funcion creada como lambda function
- g1 = u (0, t): funcion creada como lambda function
- g2 = u (a, t): funcion creada como lambda function
- a: longitud espacial (x ∈ [0, a])
- b: tiempo máximo (t ∈ [0, b])
- c: constante en la ecuación del calor
- n: número de puntos espaciales
- m: número de puntos temporales
Retorna:
- U:  matriz de tamano (m, n) con la solución aproximada de la ecuación diferencial en los 
      puntos de la malla.
"""

import numpy as np

def trisys(a, d, c, b):
    """
    Resuelve un sistema tridiagonal Ax = b usando el algoritmo de Thomas.
    - a: subdiagonal (longitud n-1)
    - d: diagonal principal (longitud n)
    - c: superdiagonal (longitud n-1)
    - b: lado derecho del sistema (longitud n)
    
    Es equivalente a la funcion del mismo nombre, incluida en MATLAB
    """
    n = len(d)
    cp = np.zeros(n-1)
    dp = np.zeros(n)

    cp[0] = c[0] / d[0]
    dp[0] = b[0] / d[0]

    for i in range(1, n-1):
        denom = d[i] - a[i-1] * cp[i-1]
        cp[i] = c[i] / denom
        dp[i] = (b[i] - a[i-1] * dp[i-1]) / denom

    dp[n-1] = (b[n-1] - a[n-2] * dp[n-2]) / (d[n-1] - a[n-2] * cp[n-2])

    # Back substitution
    x = np.zeros(n)
    x[-1] = dp[-1]
    for i in reversed(range(n-1)):
        x[i] = dp[i] - cp[i] * x[i+1]

    return x


def CrankNicolson(f, g1, g2, a, b, c, n, m):
    
    h = a / (n - 1)
    k = b / (m - 1)
    r = c**2 * k / h**2
    s1 = 2 + 2 / r
    s2 = 2 / r - 2

    U = np.zeros((n, m))
    V = np.linspace(0, b, m)

    # Condiciones de frontera
    U[0, :] = g1(V)
    U[-1, :] = g2(V)

    # Condición inicial
    U[1:-1, 0] = f(np.linspace(h, a - h, n - 2))

    # Coeficientes de la matriz tridiagonal
    Vd = np.full(n, s1)
    Vd[0] = Vd[-1] = 1
    Va = -np.ones(n - 1)
    Va[-1] = 0
    Vc = -np.ones(n - 1)
    Vc[0] = 0

    # Solución en el tiempo
    for j in range(1, m):
        Vb = np.zeros(n)
        Vb[0] = g1(k * j)
        Vb[-1] = g2(k * j)
        for i in range(1, n - 1):
            Vb[i] = U[i - 1, j - 1] + U[i + 1, j - 1] + s2 * U[i, j - 1]
        X = trisys(Va, Vd, Vc, Vb)
        U[:, j] = X

    return U.T  # Transpuesta para mantener formato de salida tipo tabla


