#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Mauricio Osorio

Método de Newton para sistemas no lineales

Resuelve un sistema de ecuaciones no lineales utilizando el método iterativo de
Newton no lineal con NumPy.

Este método itera sobre la solución del sistema, aproximando en forma vectorial
en cada iteración hasta que la solución converge dentro de una tolerancia especificada o se 
alcanza el número máximo de iteraciones.

Parámetros:
    F (array-like de tamaño (n,)): Función creada con lambda y que tiene la
      forma:  F = lambda x: [f1(x), f2(x), ... , fn(x)], donde x representa
      las variables en forma vectorial
    J (array-like de tamaño (n,n)): Matriz Jacobiana, ingresado como lambda function
      de forma análoga a como se ingresa F. 
    x0 (array-like de tamaño (n,)): Aproximación inicial de la solución.
    tol (float): Tolerancia para el criterio de parada.
    max_iter (int): Número máximo de iteraciones permitidas.

Retorna:
    x (numpy.ndarray): Vector de la solución aproximada de tamaño (n,).
    


"""
import numpy as np
import matplotlib.pyplot as plt



# Método de Newton para sistemas no lineales
def Newton_NL(F, J, x0, tol=1e-6, max_iter=100):
    x0 = np.array(x0, dtype=float)
    x = x0
    for i in range(max_iter):
        Fx = F(x)
        Jx = J(x)
        Fx = np.array(Fx, dtype=float)
        Jx = np.array(Jx, dtype=float)
       
        # Resolver el sistema J(x) * delta_x = -F(x)
        delta_x = np.linalg.solve(Jx, -Fx)
       
        # Actualizar la solución
        x = x + delta_x
       
        # Comprobar la condición de parada
        error = np.linalg.norm(delta_x, ord=2)
        iteraciones = i+1
        if error < tol:
            print(f"Convergió en {iteraciones} iteraciones.")
            return x, iteraciones, error
   
    print("No se alcanzó la convergencia.")
  
    return x, iteraciones, error






