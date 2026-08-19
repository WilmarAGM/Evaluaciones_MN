#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Mayo 2025 

@Autores:  Mauricio Osorio, a partir de la rutina existente en MATLAB

Diffin_PVF:

Resuelve un P.V.F lineal de segundo orden, de la forma
    y''(t) = p(t)y'(t) + q(t)y(t) + r(t)
    y(a) = alpha   y(b) = beta
usando el método de diferencias finitas centradas

  
Parámetros:
- p, q, r: funciones coeficientes (como funciones lambda de Python)
- a, b: extremos del intervalo
- alpha, beta: condiciones en los extremos
- N: número de subintervalos (N+1 nodos)

Devuelve:
- F: array 2D con filas [T, X], donde T es el vector de nodos y X la solución

"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.linalg import solve_banded

def Diffin_PVF(p, q, r, a, b, alpha, beta, N):
   
    h = (b - a) / N
    T_internal = np.linspace(a + h, b - h, N - 1)  # nodos interiores
    T_full = np.linspace(a, b, N + 1)              # todos los nodos

    # Vector del lado derecho B
    Vb = -h**2 * r(T_internal)
    Vb[0] += (1 + h/2 * p(T_internal[0])) * alpha
    Vb[-1] += (1 - h/2 * p(T_internal[-1])) * beta

    # Diagonal principal
    Vd = 2 + h**2 * q(T_internal)

    # Subdiagonal con j = i+1)
    Va = -1 - (h / 2) * p(T_internal[1:])  # desde el segundo nodo hasta el penúltimo

    # Superdiagonal (a_ij con j = i-1)
    Vc = -1 + (h / 2) * p(T_internal[:-1])  # desde el primer nodo hasta el antepenúltimo

    # Resolver sistema tridiagonal
    
    n = len(Vd)
    ab = np.zeros((3, n))
    ab[0, 1:] = Vc  # superdiagonal
    ab[1, :] = Vd   # diagonal principal
    ab[2, :-1] = Va # subdiagonal

    X_internal =  solve_banded((1, 1), ab, Vb) # trisys(Vc, Vd, Va, Vb)

    # Añadir condiciones de frontera
    X = np.concatenate(([alpha], X_internal, [beta]))

    # Salida final
    F = np.vstack((T_full, X)).T
    return F

