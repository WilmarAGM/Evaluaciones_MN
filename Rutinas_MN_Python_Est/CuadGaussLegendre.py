# -*- coding: utf-8 -*-

"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Mauricio Osorio

 Cuadratura de Gauss-Legendre con N nodos en el intervalo [a, b].

 Parámetros:
 - f: función a integrar (lambda o función)
 - a: límite inferior
 - b: límite superior
 - N: número de nodos

 Retorna:
 - quad: valor estimado de la integral
 - raices: raíces del polinomio de Legendre (en [-1, 1])
 - nodos: nodos transformados a [a, b]
 - coefs: coeficientes (pesos) de la cuadratura

"""

import numpy as np

def CuadGaussLegendre(f, a, b, N):
    

    # Cálculo de raíces del polinomio de Legendre P_N
    v = np.array([n / np.sqrt(4 * n**2 - 1) for n in range(1, N)])
    J = np.diag(v, -1) + np.diag(v, 1)
    raices = np.sort(np.linalg.eigvalsh(J))  # Ordenadas de menor a mayor

    # Transformación lineal al intervalo [a, b]
    nodos = 0.5 * ((b - a) * raices + (b + a))

    # Evaluación de coeficientes por el método de coeficientes indeterminados
    V = np.vander(raices, increasing=False).T
    z = np.array([(1 - (-1)**k) / k for k in range(N, 0, -1)])
    coefs = np.linalg.solve(V, z)

    # Evaluación de la cuadratura
    quad = 0.5 * (b - a) * np.sum(coefs * f(nodos))

    return quad, raices, nodos, coefs


