# -*- coding: utf-8 -*-

"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Mauricio Osorio

Método de Simpson 1/3

Aproxima el valor de la integral de una función f en un intervalo acotado [a,b]
usando la fórmula de cuadratura de Simpson 1/3 compuesto con N subintervalos


Parámetros:
    - f: función a integrar (pasar como función lambda o función definida)
    - a: límite inferior de integración
    - b: límite superior de integración
    - M: número de subintervalos (debe ser par!!)
    
Retorna:
    - s: Aproximación de la integral de f en [a, b]

"""

import numpy as np
import matplotlib.pyplot as plt


def simpson(f, a, b, M):
    
    if M % 2 == 1:
        raise ValueError("¡Error! El número de subintervalos M debe ser par.")

    h = (b - a) / M
    s1 = 0.0
    s2 = 0.0
    N = M // 2

    for k in range(1, N + 1):
        x = a + h * (2 * k - 1)
        s1 += f(x)

    for k in range(1, N):
        x = a + h * (2 * k)
        s2 += f(x)

    s = h * (f(a) + f(b) + 4 * s1 + 2 * s2) / 3
    return s

