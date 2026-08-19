#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Mauricio Osorio

Mínimos cuadrados

Calcula el polinomio que mejor se ajusta a un conjunto de puntos, de acuerdo con la
teoría de los mínimos cuadrados


Parámetros:
    x (array-like de tamaño (n, )): vector de abscisas.
    y (array-like de tamaño (n,)): vector de ordenadas.
    grado (int): grado del polinomio de ajuste 

    

Retorna:
    coeficientes (array-like de tamaño (n, )): vector con los coeficientes del polinomio ajustado
       en orden descendete de potencias de x

"""

import numpy as np
import matplotlib.pyplot as plt

def Minimos_Cuadrados(x, y, grado):

    n = len(x)
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    x = x.reshape(1, n)
    y = y.reshape(1, n)
    
    x = x.copy(); y = y.copy()
    
    
    
    if grado == 1:
        xmean = np.mean(x)
        ymean = np.mean(y)
        sumx2 = np.dot(x-xmean,np.transpose(x-xmean))
        sumxy = np.dot(y-ymean,np.transpose(x-xmean))
        
        A1 = sumxy/sumx2
        B1 = ymean - np.dot(A1,xmean)
        coeficientes = [A1,B1]
    else:
            
        # Construcción de la matriz del sistema normal X^T * X y del vector X^T * y
        F = np.zeros((n, grado + 1))
        B = np.zeros((1,grado + 1))

        for k in range(0, grado+1):
            F[:,k] = x**k
     
    
        A = np.dot(np.transpose(F),F)
        B = np.dot(np.transpose(F),np.transpose(y))
        coeficientes = np.linalg.solve(A, B)
        coeficientes = coeficientes.reshape(( grado +1,))
        coeficientes  = coeficientes[::-1]
        
              
    
    return [x.item() for x in coeficientes]





