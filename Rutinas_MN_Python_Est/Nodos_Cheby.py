#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Mauricio Osorio

Nodos de Cheebyshev

Calcula los nodos de Chebyshev en el intervalo [a, b], a partir de los ceros en [-1,1]


Parámetros:
    f -- función que se desea interpolar, ingresada como lanbda function
    a -- límite inferior del intervalo
    b -- límite superior del intervalo
    n -- número de nodos

Retorna:
    nodos_x -- array con las  abscisas de los nodos de Chebyshev 
    nodos_x -- array con las  ordenadas de los nodos de Chebyshev 

"""

import numpy as np
import matplotlib.pyplot as plt

def Nodos_cheby(f, a, b, n):

    k = np.arange(1, n + 1) # Índices de los nodos
    nodos_x = np.cos((2 * k - 1) / (2 * n) * np.pi) # Nodos en [-1, 1]

    # Transformar los nodos al intervalo [a, b]
    nodos_x = 0.5 * (a + b) + 0.5 * (b - a) * nodos_x
    nodos_y = f(nodos_x)

    return nodos_x,  nodos_y


