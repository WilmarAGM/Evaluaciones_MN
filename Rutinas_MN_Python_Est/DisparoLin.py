#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Mayo 2025 

@Autores:  Mauricio Osorio, a partir de la rutina existente en MATLAB

DisparoLin:

Resuelve un P.V.F lineal de segundo orden, de la forma
    y''(t) = p(x)y'(x) + q(x)y(x) + r(x)
    y(a) = alpha   y(b) = beta
usando el método del disparo lineal

  
Parámetros:
- F1 y F2 son los sistemas de ecuaciones de primer orden representando los
  Problemas de Valor Inicial (P.V.I.'s), espectivamente; funciones creadas con lambda
- a y b son los extremos del intervalo
- alpha = x(a)  y  beta = x(b); las condiciones frontera
- M es el numero de pasos

Retorna:
L = [T', X]; donde  T' es el vector de abscisas (M+1) x 1
           y  X  es el vector de ordenadas  (M+1) x 1

"""


import numpy as np
import matplotlib.pyplot as plt
from RK4_sist import RK4_sist



def DisparoLin(F1, F2, a, b, alpha, beta, M):
    
    # Resolver el sistema con F1
    Za = [alpha, 0];
    [T, Z] = RK4_sist(F1, a, b, Za, M)
    U = Z[:, 0]
    
    # Resolver el sistema con F2
    Za = [0, 1];
    [T, Z] = RK4_sist(F2, a, b, Za, M)
    V = Z[:, 0]
    
    # Calcular la solucion al problema de valor frontera
    X = U + (beta - U[M]) * V / V[M]
    L = np.column_stack((T, X))
    
    return L


