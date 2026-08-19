#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Mayo 2025 

@Autores:  Mauricio Osorio, a partir de la rutina existente en MATLAB

RK3_Heun:

Resuelve la ecuacion diferencial y'(t) = f(t,y), usando el método de Runge 
Kutta 3, en la versión de Heun'

  
Parámetros:
- f = funcion de t y y, creada como lambda function
- a, b: extremos del intervalo temporal [a, b]
- ya:  valor de y(a), es decir, la condición inicial
- M: número de pasos

Retorna:
- E = [T', Y'] donde T es el vector de abscisas y Y es el vector de ordenadas

"""


import numpy as np
import matplotlib.pyplot as plt
def RK3_Heun(f, a, b, ya, M):
    
    h = (b - a) / M
    
    T = np.zeros(M+1)
    Y = np.zeros(M+1)
    T = np.linspace(a, b, M + 1)
    
    Y[0] = ya

    for  j in range(0,M):
        k1 =  f(T[j], Y[j])
        k2 =  f(T[j]+h/3, Y[j]+(h/3)*k1)
        k3 =  f(T[j]+2*h/3, Y[j]+(2*h/3)*k2)
        Y[j+1] = Y[j] + (h/4) * (k1+3*k3)
        
    E = np.column_stack((T, Y))
    
    
    return E



