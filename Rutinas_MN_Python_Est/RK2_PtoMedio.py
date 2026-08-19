#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Mayo 2025 

@Autores:  Mauricio Osorio, a partir de la rutina existente en MATLAB

Punto Medio:

Resuelve la ecuacion diferencial y'(t) = f(t,y), usando el método de Rnge Kutta 2,
en la versión del punto medio'

  
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
def RK2_PtoMedio(f, a, b, ya, M):
    
    h = (b - a) / M
    
    T = np.zeros(M+1)
    Y = np.zeros(M+1)
    T = np.linspace(a, b, M + 1)
    
    Y[0] = ya

    for  j in range(0,M):
        k1 =  f(T[j], Y[j])
        Y[j+1] = Y[j] + h * f(T[j]+h/2, Y[j]+(h/2)*k1)
        
    E = np.column_stack((T, Y))
    
    
    return E


