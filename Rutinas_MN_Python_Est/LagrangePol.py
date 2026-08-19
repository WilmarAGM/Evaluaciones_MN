#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores:  Manuela Bastidas, Mauricio Osorio, ChatGPT

LagrangePol: 
    
Encuentra el polinomio interpolante de Lagrange para un conjunto de datos.

Parámetros:
- x_values: valores de las abscisass de los puntos
- y_values: valores de las ordenadas de los puntos

Retorna:
- pol: El polinomio interpolante de Lagrange
- coeficientes:  Los coeficientes del polinomio, ordenados de mayor a menor potencia



"""


import sympy as sp

def LagrangePol(x_values, y_values):
    """Genera el polinomio de interpolación de Lagrange de manera simbólica."""
    x = sp.Symbol('x')
    n = len(x_values)
    polynomial = 0
    
  
    for i in range(n):
        term = y_values[i]
        li = 1
        for j in range(n):
            if i != j:
                li *= (x - x_values[j]) / (x_values[i] - x_values[j])
                
        polynomial += term * li
            
    pol = sp.expand(polynomial)
    #print(f"El polinomio interpolante de Lagrange es: y= {pol}")
    
    coeficientes = sp.Poly(pol, x).all_coeffs()
   #print("Que tiene como coeficientes (ordenados de mayor a menor grado):", coeficientes)
    
    
    return pol,  coeficientes



