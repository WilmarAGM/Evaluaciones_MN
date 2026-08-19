# -*- coding: utf-8 -*-
"""
Created on Tue Apr 29 11:19:06 2025

@author: UNALMED
"""

import numpy as np
from scipy.sparse import diags, kron, eye

def NeumannM(N):
    n = int(np.sqrt(N))
    if n * n != N:
        raise ValueError("N debe ser un cuadrado perfecto.")
    
    # Matriz T con -2 en las subdiagonales y 4 en la diagonal
    e = np.ones(n)
    T = diags([-2*e, 4*e, -2*e], [-1, 0, 1], shape=(n, n))
    
    # Matriz S con -1 en subdiagonales
    S = diags([-1*e, -1*e], [-1, 1], shape=(n, n))
    
    # Matriz Kronecker
    A = kron(eye(n), T) + kron(S, eye(n))

    return A.todense()
# print(A.toarray()) 