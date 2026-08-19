#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Mauricio Osorio
Descripción: Rutina que grafica un spline obtenido para un conjunto de datos

"""

import numpy as np
import matplotlib.pyplot as plt



# Función para evaluar el spline cúbico en cualquier punto
def evaluate_spline(x_points, a, b, c, d, x):
    n = len(x_points) - 1
    for i in range(n):
        if x_points[i] <= x <= x_points[i+1]:
            dx = x - x_points[i]
            return a[i] + b[i] * dx + c[i] * dx**2 + d[i] * dx**3
    return None


def GraficaSpline(x,y,S):
    d=S[:,0]
    c=S[:,1]
    b=S[:,2]
    a=S[:,3]
    # Evaluar el spline en puntos intermedios para graficar
    x_vals = np.linspace(x[0], x[-1], 1000)
    y_vals = np.array([evaluate_spline(x, a, b, c, d, xp) for xp in x_vals])

    # Graficar los resultados
    plt.plot(x, y, 'ro', label="Puntos de interpolación")
    plt.plot(x_vals, y_vals, 'b-', label="Spline cúbico")
    plt.legend()
    plt.xlabel("x")
    plt.ylabel("y")
    plt.title("Spline Cúbico")
    plt.grid(True)
    plt.show()
    
    return None