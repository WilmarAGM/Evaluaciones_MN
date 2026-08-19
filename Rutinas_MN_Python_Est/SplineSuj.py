#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Mauricio Osorio

Spline cúbico sujeto

Este método encuentra el spline cúbico sujeto que se ajusta a un conjunto de datos,
usando el método de solución de un sistema tridiagonal para las segundas derivadas 
en los nodos de interpolación.

Parámetros:
    X (array-like de tamaño (1, n)): Vector de abscisas.
    Y (array-like de tamaño (1, n)): Vector de ordenadas.
    fpa : Derivada en el extremo izquierdo
    fpb : Derivada en el extremo derecho

Retorna:
    S (array-like de tamaño (n-1, 4)) : Matriz cuyos filas son los coeficientes de 
    los tramos del spline cúbico, de la forma:  fila i = [d_i c_i b_i a_i], donde
    S_i(x) = a_i + b_i(x-x_i) + c_i(x-x_i)^2 + d_i(x-x_i)^3  para x_[i-1]< x< x[i]
    

"""

import numpy as np


# Función para resolver el sistema del spline cúbico sujeto

def SplineSuj(X, Y, fpa, fpb):

    X = np.array(X, dtype=float)
    Y = np.array(Y, dtype=float)
    x = X.copy(); y = Y.copy()
    
    n = len(x) - 1  # Número de subintervalos
    h = np.diff(x)  # Diferencias entre nodos

    
    if n <=2: raise Exception('No aplica el método para datos con tamaño n =< 3')
    
    d = np.diff(y)/h
    a = h[1:n-1].copy()
    b = 2*(h[0:n-1]+h[1:n])
    c = h[1:n-1].copy()
    u = 6*np.diff(d)
    
    # Restricciones de los trazadores sujetos en los extremos
    
    b[0] = b[0] -  h[0]/2
    u[0] = u[0] - 3*(d[0] - fpa)
    b[n-2] = b[n-2] -  h[n-1]/2
    u[n-2] = u[n-2] - 3*(fpb - d[n-1])
    
      
    for k in range(1,n-1):
        temp = a[k-1]/b[k-1]
        b[k] = b[k] - temp*c[k-1]
        u[k] = u[k] - temp*u[k-1]
        
    M = np.zeros((n+1, ))  
    M[n-1] = u[n-2]/b[n-2]
    
   
    
    for j in range(n-3,-1,-1):
        M[j+1] = (u[j] - c[j]*M[j+2])/b[j]
        
        
    # restricciones en los extremos    
    
    M[0] = 3*(d[0] - fpa)/h[0] - M[1]/2
    M[-1] = 3*(fpb - d[n-1])/h[n-1] - M[n-1]/2
   
    
    S = np.zeros((n,4))

    for k in range(0, n):
        S[k,0] = (M[k+1]-M[k])/(6*h[k])
        S[k,1] = M[k]/2
        S[k,2] = d[k]-h[k]*(2*M[k]+M[k+1])/6
        S[k,3] = y[k] 
    
     

    return S



