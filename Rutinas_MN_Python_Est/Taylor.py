#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Mayo 2025 

@Autores:  Mauricio Osorio, a partir de la rutina existente en MATLAB

Taylor:

Resuelve la ecuacion diferencial y'(t) = f(t,y), usando el método de Taylor
hasta el cuarto orden

  
Parámetros:
- df = función que devuelve [y', y'', y''', y''''] evaluada en (t, y), 
       creada como lambda function.  Si solo se va a usar Taylor de orden 2, por
       ejemplo, entonces se ingresa y'''=y''''=0
- a, b: extremos del intervalo temporal [a, b]
- ya:  valor de y(a), es decir, la condición inicial
- M: número de pasos

Retorna:
- T4 = [T', Y'] donde T es el vector de abscisas y Y es el vector de ordenadas, 
       es decir, matriz 2D con T[:, 0] = t, T[:, 1] = y

"""


import numpy as np
import matplotlib.pyplot as plt

def Taylor(df, a, b, ya, M):
  
    h = (b - a) / M
    T = np.linspace(a, b, M + 1)
    Y = np.zeros(M + 1)
    Y[0] = ya

    for j in range(M):
        D = df(T[j], Y[j])  # D = [y', y'', y''', y'''']
        Y[j + 1] = Y[j] + h * (D[0] + h * (D[1] / 2 + h * (D[2] / 6 + h * D[3] / 24)))

    T4 = np.column_stack((T, Y))
    return T4

