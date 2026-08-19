#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores:  Manuela Bastidas, Mauricio Osorio, ChatGPT

NewtonPol: 
    
Encuentra el polinomio interpolante de Newton para un conjunto de datos.

Parámetros:
- x_values: valores de las abscisass de los puntos
- y_values: valores de las ordenadas de los puntos

Retorna:
- pol: El polinomio interpolante de Lagrange
- coeficientes:  Los coeficientes del polinomio, ordenados de mayor a menor potencia




"""


import sympy as sp
import numpy as np   
   

def NewtonPol(x_values, y_values):
    """Calcula la tabla de diferencias divididas de Newton."""
    n = len(x_values)
    Difdiv = np.zeros((n,n))
    
       # Llenar la primera columna con valores de y
    for i in range(n):
        Difdiv[i][0] = y_values[i]

    # Calcular las diferencias divididas
    for j in range(1, n):
        for i in range(j,n):
            Difdiv[i][j] = (Difdiv[i][j-1] - Difdiv[i-1][j-1]) / (x_values[i] - x_values[i-j])

    # Extraer los coeficientes de la diagonal superior
    #print("la tabla de diferencias divididas es:")
    # print()
    # print(coef)
    # print()
    """Genera el polinomio de interpolación de Newton de manera simbólica."""
    x = sp.Symbol('x')
    coef = np.diag(Difdiv)
    
    n = len(x_values)
    
    polynomial = coef[0]
    product_terms = 1

    for i in range(1, n):
        product_terms *= (x - x_values[i-1])
        polynomial += coef[i] * product_terms
        
    poly=sp.expand(polynomial)
    
    #print(f"El polinomio interpolante de Newton es: y= {poly}")
    
    coeficientes = sp.Poly(poly, x).all_coeffs()
   
    #print("Que tiene como coeficientes (ordenados de mayor a menor grado):", coeficientes)
    
   
    return Difdiv, poly, coeficientes
    
   
   



