#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Gustavo Pérez, Manuela Bastidas, Mauricio Osorio


Método de Newton-Raphson acelerado: 
    
El método de Newton-Raphson acelerddo para encontrar una raíz de la función f.

Parámetros:
- f (función): La función cuya raíz se busca.
- df (función): La derivada de la función f.
- p0 (float): Aproximación inicial de la raíz.
- m (float):  la multiplicidad de la raíz
- tol (float): Tolerancia para el criterio de convergencia (por defecto 1e-6).
- max_iter (int): Número máximo de iteraciones permitidas (por defecto 100).

Retorna:
- p (float): Una aproximación de la raíz.
- None: Si el método no converge dentro de max_iter iteraciones.

Excepciones:
- ZeroDivisionError: Si la derivada df(p) es cero en alguna iteración.
"""

import numpy as np
import matplotlib.pyplot as plt


def newton_acel(f, df, p0, m, tol, max_iter):

    p = p0  # Aproximación actual
    for n in range(1, max_iter + 1):
        f_p = f(p)
        df_p = df(p)
        
        if df_p == 0:
            raise ZeroDivisionError(f"La derivada es cero en la iteración {n}. No se encontró solución.")
        
        # Calcular la siguiente aproximación
        p_next = p - m*f_p / df_p
        
        # Verificar convergencia
        if abs(p_next - p) < tol:
            print(f"Convergió a {p_next} después de {n} iteraciones.")
            return p_next
        
        p = p_next  # Actualizar la aproximación
    
    # Si no se alcanza la convergencia dentro de max_iter iteraciones
    print(f"No convergió después de {max_iter} iteraciones.")
    return None


