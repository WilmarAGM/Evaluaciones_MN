# -*- coding: utf-8 -*-
"""
Created on Mon Mar 31 11:05:49 2025

@author: UNALMED
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Mauricio Osorio

Spline cúbico conocido

Este método encuentra el spline cúbico con curvatura conocida en los extremos
que se ajusta a un conjunto de datos, usando el método de solución de un sistema
tridiagonal para las segundas derivadas en los nodos de interpolación.

Parámetros:
    X (array-like de tamaño (1, n)): Vector de abscisas.
    Y (array-like de tamaño (1, n)): Vector de ordenadas.
    Sa : valor de la segunda derivada en el extremo izquierdo
    Sb : valor de la segunda derivada en el extremo derecho
    

Retorna:
    S (array-like de tamaño (n-1, 4)) : Matriz cuyos filas son los coeficientes de 
    los tramos del spline cúbico, de la forma:  fila i = [d_i c_i b_i a_i], donde
    S_i(x) = a_i + b_i(x-x_i) + c_i(x-x_i)^2 + d_i(x-x_i)^3  para x_[i-1]< x< x[i]
    

"""

import numpy as np


# Función para resolver el sistema del spline cúbico conocido

def SplineConoc(X, Y, Sa, Sb):
    
    X = np.array(X, dtype=float)
    Y = np.array(Y, dtype=float)
    x = X.copy(); y = Y.copy() 
    
    n = len(x) - 1 # Número de subintervalos
    h = np.diff(x) # Diferencias entre nodos    
    d = np.diff(y)/h    
    u = 6*np.diff(d)
    
    if n <=2: raise Exception('No aplica el método para datos con tamaño n =< 3')
    
    
    b = 2*(h[0:n-1] + h[1:n])
    c = h[1:n-1].copy()
    u[0] = u[0] - h[0]*Sa
    u[n-2] = u[n-2] - h[n-1]*Sb 
    
    
    # Construcción de la matriz tridiagonal
    
    T = np.diag(c, -1) + np.diag(b, 0) + np.diag(c, 1)
    
    # Solución del sistema
    ma = np.linalg.solve(T,u)
    
    M = np.zeros((n+1, )) 
    M[1:n] = ma
    
    M[0] = Sa
    M[-1] = Sb
    
    S = np.zeros((n,4))
    for k in range(0, n):
        S[k,0] = (M[k+1]-M[k])/(6*h[k])
        S[k,1] = M[k]/2
        S[k,2] = d[k]-h[k]*(2*M[k]+M[k+1])/6
        S[k,3] = y[k] 
    
    
    return S


