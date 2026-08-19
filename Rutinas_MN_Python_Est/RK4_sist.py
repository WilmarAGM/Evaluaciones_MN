
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Mayo 2025 

@Autores:  Mauricio Osorio, a partir de la rutina existente en MATLAB

RK4_sist:

Resuelve un sistema de ecuaciones diferenciales de primer orden, usando el
 método de Runge Kutta de cuarto orden, en su forma vectorial'

  
Parámetros:
- F = funcion de t y U, de manera vectorial, creada como lambda function
      F(t,U)=[f1(t,U), ..., fn(t,U)]
- a, b: extremos del intervalo temporal [a, b]
- Za:  valor de condiciones iniciales [x1(a), ..., xn(a)]
- M: número de pasos

Retorna:
- T: vector de pasos
- Z: Matriz con [x1(t), ..., xn(t)]

"""


import numpy as np
import matplotlib.pyplot as plt
def RK4_sist(F, a, b, Za, M):
    
    Za = np.array(Za, dtype=float).reshape(-1, 1)
    
    h = (b - a) / M
    
    T = np.zeros(M+1)
    Z = np.zeros((M + 1, len(Za)))
    T = np.linspace(a, b, M + 1)
    
    Z[0,:] = Za.flatten()

    for  j in range(0,M):
        k1 =  F(T[j], Z[j, :])
        k1 = h*np.array(k1, dtype=float)
        k2 =  F(T[j]+h/2, Z[j, :]+(1/2)*k1)
        k2 = h*np.array(k2, dtype=float)
        k3 =  F(T[j]+h/2, Z[j, :]+(1/2)*k2)
        k3 = h*np.array(k3, dtype=float)
        k4 =  F(T[j]+h, Z[j, :]+k3)
        k4 = h*np.array(k4, dtype=float)
        Z[j+1, :] = Z[j, :] + (1/6) * (k1+2*k2+2*k3+k4)    
    
    return T, Z



