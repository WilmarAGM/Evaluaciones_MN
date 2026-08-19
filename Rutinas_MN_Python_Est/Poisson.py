#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores:  Mauricio Osorio, a partir de la rutina existente en MATLAB y con
           la ayuda de una IA

Poisson: 
    
Resuelve el problema de Poisson u_{xx} + u_{yy} = g(x,y) en [a,b] x [c,d], 
usando el metodo de diferencias finitas de cinco puntos
 
Parámetros:
- g funcion creada con lambda
- f1 es la condicion de frontera abajo (en y=c) funcion creada con lambda
- f2 es la condicion de frontera derecha (en x=b) funcion creada con lambda
- f3 es la condicion de frontera arriba (en y=d) funcion creada con lambda
- f4 es la condicion de frontera izquierda (en x=a) funcion creada con lambda
- m es el numero de puntos sobre el eje x
- n es el numero de puntos sobre el eje y

Retorna:
- U:  matriz con la solución aproximada de la ecuación diferencial en los 
      puntos de la malla.
"""

import numpy as np
from scipy.sparse import kron, diags, eye
from scipy.sparse.linalg import spsolve

def Poisson(g, f1, f2, f3, f4, a, b, c, d, m, n):
    mx = m - 2
    my = n - 2
    h = (b - a) / (m - 1)
    k = (d - c) / (n - 1)

    x = np.linspace(a, b, mx + 2)
    y = np.linspace(c, d, my + 2)

    X, Y = np.meshgrid(x, y, indexing='ij')

    Iint = slice(1, mx + 1)
    Jint = slice(1, my + 1)

    Xint = X[Iint, Jint]
    Yint = Y[Iint, Jint]

    rhs = g(Xint, Yint)

    v1 = f1(x[1:mx+1])
    v3 = f3(x[1:mx+1])
    v2 = f2(y[1:my+1])
    v4 = f4(y[1:my+1])

    # Ajustes por condiciones de frontera
    rhs[:, 0] -= v1 / k**2
    rhs[:, -1] -= v3 / k**2
    rhs[0, :] -= v4 / h**2
    rhs[-1, :] -= v2 / h**2

    # Vector columna
    F = rhs.reshape((mx* my), order='F')

    # Matrices dispersas
    I1 = eye(mx)
    I2 = eye(my)

    e1 = np.ones(mx)
    e2 = np.ones(my)

    T1 = diags([e1, -2*e1, e1], [-1, 0, 1], shape=(mx, mx))
    T2 = -2 * eye(mx)
    S2 = diags([e2, e2], [-1, 1], shape=(my, my))

    A1 = kron(I2, T1) / h**2
    A2 = (kron(I2, T2) + kron(S2, I1)) / k**2

    A = A1 + A2
    
    A = A.tocsr()

    uvec = spsolve(A, F)

    usoln = np.zeros((m, n))
    usoln[Iint, Jint] = uvec.reshape((mx, my), order='F')  

    # Fronteras
    w2 = f2(y)
    w4 = f4(y)
    U = usoln[1:mx+1, 1:my+1]
    U = np.column_stack((v1, U, v3))
    U = np.vstack((w4, U, w2))
    return U.T






