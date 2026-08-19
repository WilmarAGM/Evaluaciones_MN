# -*- coding: utf-8 -*-

"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Mauricio Osorio

Método del trapecio

Aproxima el valor de la integral de una función f en un intervalo acotado [a,b]
usando la fórmula de cuadratura del trapecio compuesto con N subintervalos


Parámetros:
    - f: función a integrar (pasar como función lambda o función definida)
    - a: límite inferior de integración
    - b: límite superior de integración
    - M: número de subintervalos
    
Retorna:
    - s: Aproximación de la integral de f en [a, b]

"""

import numpy as np
import matplotlib.pyplot as plt


def trapecio(f, a, b, M):
   
    h = (b - a) / M
    s = 0.0

    for k in range(1, M):
        x = a + h * k
        s += f(x)

    s = h * (f(a) + f(b)) / 2 + h * s
    return s


