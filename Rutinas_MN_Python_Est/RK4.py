#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Mayo 2025 

@Autores:  Mauricio Osorio, a partir de la rutina existente en MATLAB

RK4:

Resuelve la ecuacion diferencial y'(t) = f(t,y), usando el método de Runge 
Kutta de cuarto orden'

  
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
def RK4(f, a, b, ya, M):
    
    h = (b - a) / M
    
    T = np.zeros(M+1)
    Y = np.zeros(M+1)
    T = np.linspace(a, b, M + 1)
    
    Y[0] = ya

    for  j in range(0,M):
        k1 =  h*f(T[j], Y[j])
        k2 =  h*f(T[j]+h/2, Y[j]+(1/2)*k1)
        k3 =  h*f(T[j]+h/2, Y[j]+(1/2)*k2)
        k4 =  h*f(T[j]+h, Y[j]+k3)
        Y[j+1] = Y[j] + (1/6) * (k1+2*k2+2*k3+k4)
        
    E = np.column_stack((T, Y))
    
    
    return E


