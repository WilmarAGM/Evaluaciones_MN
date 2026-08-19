#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Jacobo Zapata, Mauricio Osorio

Método de SOR

Resuelve el sistema de ecuaciones lineales Ax = b utilizando el método iterativo de SOR 
con NumPy.

Este método itera sobre la solución del sistema, aproximando en forma escalar
en cada iteración, hasta que la solución converge dentro de una tolerancia especificada o se 
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
# import matplotlib.pyplot as plt
 

def SOR(A, b, x0, w, epsilon, max_iter):
    
   A = np.array(A, dtype=float)
   b = np.array(b, dtype=float).reshape(-1, 1)
   x0 = np.array(x0, dtype=float).reshape(-1, 1)

   # Check if omega is in valid range
   if w <= 0 or w >= 2:
       raise ValueError("El parámetro de relajación debe estar en (0, 2)")

   n = A.shape[0]
   if A.shape[1] != n:
       raise ValueError("Matriz A no es cuadrada")
   if b.shape[0] != n:
       raise ValueError(
           f"Error de dimensión: A es {n}x{n}, pero b tiene {b.shape[0]} filas"
       )
   if x0.shape[0] != n:
       raise ValueError(
           f"Error de dimensión: A es {n}x{n}, pero x0 tiene {x0.shape[0]} elementos"
       )

  
   if np.any(np.diag(A) == 0):
       raise ValueError("La diagonal de A contiene ceros.  El método no se puede usar")

   N = len(b)
   x0 = x0.flatten()
   b = b.flatten()
   Y = x0.copy()
   X = np.zeros(N)
   iteraciones = 0

   for k in range(max_iter):
       for j in range(N):
           if j == 0:
               X[0] = (b[0] - np.dot(A[0, 1:], x0[1:])) / A[0, 0]
               Y[0] = (1 - w) * x0[0] + w * X[0]
           elif j == N - 1:
               X[N - 1] = (b[N - 1] - np.dot(A[N - 1, :N - 1], Y[:N - 1])) / A[N - 1, N - 1]
               Y[N - 1] = (1 - w) * x0[N - 1] + w * X[N - 1]
           else:
               sum1 = np.dot(A[j, :j], Y[:j])
               sum2 = np.dot(A[j, j+1:], x0[j+1:])
               X[j] = (b[j] - sum1 - sum2) / A[j, j]
               Y[j] = (1 - w) * x0[j] + w * X[j]

       iteraciones = iteraciones + 1
       err = np.linalg.norm(Y - x0)
       relerr = err / (np.linalg.norm(Y) + np.finfo(float).eps)        
   

       if err < epsilon or relerr < epsilon:
           break

       x0 = Y.copy()

   Y = Y.reshape(-1,1)
   return Y, iteraciones, err







