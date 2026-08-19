#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores:  Mauricio Osorio, a partir de la rutina existente en MATLAB y con
           la ayuda de una IA

DifinHiper:

Resuelve la ecuacion de onda, u_{tt} = c^2 u_{xx}  para x in [0,a]  y t en [0,b],
con el metodo de dferencias finitas centradas en tiempo y en espacio con condicion
inicial mejorada 

  
Parámetros:
- f = u (x, 0): funcion creada como lambda function
- g = u_t (x, 0): funcion creada como lambda function
- q1: condición de frontera izquierda u(0, t) creada como lambda function
- q2: condición de frontera derecha u(a, t) creada como lambda function
- a, b: extremos de los intervalos [0, a] y [0,b]
- c: constante en la ecuación de onda
- n: número de puntos espaciales
- m: número de puntos temporales
Retorna:
- U:  matriz de tamano (m, n) con la solución aproximada de la ecuación diferencial en los 
      puntos de la malla, donde cada fila es un instante de tiempo
"""

import numpy as np

def DifinHiper(f, g, q1, q2, a, b, c, n, m):
    
    h = a / (n - 1)
    k = b / (m - 1)
    r = c * k / h
    # print(r)
    r2 = r**2
    r22 = r2 / 2
    s1 = 1 - r2
    s2 = 2 - 2 * r2

    U = np.zeros((n, m))

    # Primera fila: t = 0
    for i in range(1, n - 1):
        xi = i * h
        U[i, 0] = f(xi)
        U[i, 1] = (s1 * f(xi) + k * g(xi) + r22 * (f(xi + h) + f(xi - h)))

    # Condiciones de frontera
    for j in range(m):
        t = j * k
        U[0, j] = q1(t)
        U[-1, j] = q2(t)

    # Esquinas (t = 0)
    U[0, 0] = f(0)
    U[-1, 0] = f(a)

    # Iteración en el tiempo
    for j in range(2, m):
        for i in range(1, n - 1):
            U[i, j] = (s2 * U[i, j - 1] + r2 * (U[i - 1, j - 1] + U[i + 1, j - 1])- U[i, j - 2])
            

    return U.T  # Transpuesta para que filas representen el tiempo

