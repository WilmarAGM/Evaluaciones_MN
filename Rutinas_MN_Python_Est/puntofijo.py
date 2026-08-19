#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Gustavo Pérez, Manuela Bastidas, Mauricio Osorio


Punto Fijo: 

El método de iteración de punto fijo para encontrar un punto fijo 
de una función g.

Parámetros:
- g: Función para la cual se busca el punto fijo.
- p0: Aproximación inicial.
- tol: Tolerancia para el criterio de convergencia.
- max_iter: Número máximo de iteraciones permitidas.

Retorna:
- p: Aproximación del punto fijo.
- None: Si no converge dentro del número máximo de iteraciones.

"""

import numpy as np  
import matplotlib.pyplot as plt
import pandas as pd


# Definición del método de punto fijo
def punto_fijo(g, p0, tol, max_iter):
    
    # Punto inicial
    p = p0
    data = []
    for n in range(1, max_iter + 1):
        p_next = g(p)
        e=np.abs(p_next - p)
               
        data.append([n, p_next, e])
        
        # Verificar si la diferencia es menor que la tolerancia
        if e < tol:
            print(pd.DataFrame(data,columns=["Iteración", "p", "Error = |p_n - P-(n-1)|"]))            
            print()
            print(f"Convergió en {n} iteraciones.")
            print()
            print(f'La aproximación al punto fijo es: {p_next}') 
            
            
            return p_next
        
        p = p_next
        
    # Si no converge dentro del número máximo de iteraciones
    print(f"No convergió después de {max_iter} iteraciones.")
    return None



