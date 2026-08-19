#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Jacobo Zapata, Mauricio Osorio

Método de Jacobi

Resuelve el sistema de ecuaciones lineales Ax = b utilizando el método iterativo de Jacobi con NumPy.

Este método itera sobre la solución del sistema, aproximando en forma escalar
en cada iteración hasta que la solución converge dentro de una tolerancia especificada o se 
alcanza el número máximo de iteraciones.

Parámetros:
    A (array-like de tamaño (n, n)): Matriz de coeficientes.
    b (array-like de tamaño (n,)): Vector del lado derecho de la ecuación.
    x0 (array-like de tamaño (n,)): Aproximación inicial de la solución.
    epsilon (float): Tolerancia para el criterio de parada.
    max_iter (int): Número máximo de iteraciones permitidas.

Retorna:
    x_new (numpy.ndarray): Vector de la solución aproximada de tamaño (n,).
    iteraciones (int): Número de iteraciones realizadas.
    error (array) : Vector con los errores en cada iteración

Excepciones:
    ValueError: Si la matriz A no es cuadrada o si algún elemento diagonal a_ii es cero, 
                lo que impide el correcto cálculo del método.

"""

import numpy as np

def Jacobi(A, b, x0, epsilon, max_iter):
    # Inicializacion de los array
    A = np.array(A, dtype=float)
    b = np.array(b, dtype=float).reshape(-1, 1)
    x = np.array(x0, dtype=float).reshape(-1, 1)

    n = A.shape[0]
    X = np.zeros_like(x)
    
    
    if A.shape[1] != n:
        raise ValueError("Matriz A no es cuadrada")
    if b.shape[0] != n:
        raise ValueError(
            f"Error de dimensión: A es {n}x{n}, pero b tiene {b.shape[0]} filas"
        )
    if x.shape[0] != n:
        raise ValueError(
            f"Error de dimensión: A es {n}x{n}, pero x0 tiene {x0.shape[0]} elementos"
        )

    if np.any(np.diag(A) == 0):
        raise ValueError("La diagonal de A contiene ceros.  El método no se puede usar")

    iteraciones = 0
    for k in range(max_iter):
        for j in range(n):
            sum_ = np.dot(A[j, :j], x[:j]) + np.dot(A[j, j+1:], x[j+1:])
            X[j] = (b[j] - sum_) / A[j, j]

        err = np.linalg.norm(X - x)
        relerr = err / (np.linalg.norm(X) + np.finfo(float).eps)
        x = X.copy()
        iteraciones = k + 1
        if err < epsilon or relerr < epsilon:
            break

    return x, iteraciones, err



