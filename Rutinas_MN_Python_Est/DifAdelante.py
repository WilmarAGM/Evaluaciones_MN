#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores:  Mauricio Osorio, a partir de la rutina existente en MATLAB y con
           la ayuda de una IA

DifAdelante:

Resuelve la ecuacion del calor, u_{t} = c^2 u_{xx}  para x in [0,a]  y t en [0,b],
 con el metodo de diferencias finitas progresivas en tiempo y centrado en espacio

  
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

def DifAdelante(f, g1, g2, a, b, c, n, m):
    
    h = a / (n - 1)
    k = b / (m - 1)
    r = c**2 * k / h**2
    s = 1 - 2 * r

    U = np.zeros((n, m))
    V = np.linspace(0, b, m)

    # Condiciones de frontera
    U[0, :] = g1(V)
    U[-1, :] = g2(V)

    # Condición inicial (fila inicial en x, t=0)
    U[1:-1, 0] = f(np.linspace(h, a - h, n - 2))

    # Iteración del esquema en el tiempo
    for j in range(1, m):
        for i in range(1, n - 1):
            U[i, j] = s * U[i, j - 1] + r * (U[i - 1, j - 1] + U[i + 1, j - 1])

    return U.T


