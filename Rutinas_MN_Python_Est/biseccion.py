#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Gustavo Pérez, Manuela Bastidas, Mauricio Osorio

Bisección: 
    
Encuentra una raíz aproximada de una función continua f dentro de un intervalo [a, b] usando el método de bisección.

Parámetros:
- f (función): La función cuya raíz se desea encontrar. Debe ser continua en [a, b].
- a (float): Inicio del intervalo.
- b (float): Fin del intervalo.
- tol (float): La tolerancia para la aproximación de la raíz. El algoritmo se detiene cuando el error es menor que este valor.
- max_iter (int): El número máximo de iteraciones para evitar bucles infinitos si no se alcanza la convergencia.

Retorna:
- float: Un valor aproximado de la raíz de la función f en el intervalo [a, b].
- None: Retorna None si no se encuentra una raíz o si se alcanza el número máximo de iteraciones.

Excepciones:
- ValueError: Si f(a) y f(b) no tienen signos opuestos, lo que significa que no se garantiza una raíz en [a, b].
"""


import numpy as np  
import matplotlib.pyplot as plt
import pandas as pd

def biseccion(f, a, b, tol, max_iter):
    
    # Verificar si el intervalo es adecuado para el método de bisección
    if f(a) * f(b) > 0:
        print('Error: El intervalo no es válido para el método de bisección.')
        return None  # Detener la ejecución si no hay cambio de signo
    elif f(a) == 0:
        print('La raíz está en a')
        return a  
    elif f(b) == 0:
        print('La raíz está en b')
        return b
        
        
    # Inicializar variables
    a0 = a
    b0 = b
    contador_iteraciones = 0  # Inicializar el contador de iteraciones
    data = []

    while contador_iteraciones < max_iter:
        contador_iteraciones += 1  # Incrementar el contador de iteraciones

        # Calcular el punto medio del intervalo
        p0 = a0 + (b0 - a0) / 2
        fp0 = f(p0)
        fa0 = f(a0)
        fb0 = f(b0)
        data.append([contador_iteraciones, a0, p0, b0, fa0, fp0, fb0 ])

        # Verificar si el punto medio es la raíz o si el error es aceptable
        if abs(f(p0)) < 1e-10 or (b0 - a0) / 2 < tol:            
            print(pd.DataFrame(data, columns=["Iteración", "a", "p", "b", "f(a)", "f(p)", "f(b)"]))
            print()
            print(f'Número de iteraciones: {contador_iteraciones}')
            print()
            print(f'La aproximación a la raíz es: {p0}') 
            return p0# Retornar la raíz aproximada

        # Determinar en qué subintervalo continuar la búsqueda
        if f(a0) * f(p0) < 0:
            b0 = p0  # La raíz está en [a0, p0]
        elif f(p0) * f(b0) < 0:
            a0 = p0  # La raíz está en [p0, b0]
        else:
            # Caso en el que f(p0) es cero o muy cercano a cero
            print(pd.DataFrame(data, columns=["Iteración", "a", "p", "b", "f(a)", "f(p)", "f(b)" ]))
            print()
            print(f'Número de iteraciones: {contador_iteraciones}')
            print()
            print(f'La aproximación a la raíz es: {p0}') 
            return p0 # Retornar la raíz exacta o aproximada

    # Si se alcanza el número máximo de iteraciones sin convergencia
    print('Error: Se alcanzó el número máximo de iteraciones sin convergencia.')
    return None






