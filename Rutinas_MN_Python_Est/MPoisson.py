# -*- coding: utf-8 -*-
"""
Created on Sun Apr 27 21:09:09 2025

@author: Mauricio
"""

import scipy.sparse as sp

def MPoisson(n):
    """Equivalente a gallery('poisson', n) de MATLAB"""
    I = sp.eye(n, format='csr')
    e = sp.diags([-1, 4, -1], [-1, 0, 1], shape=(n, n), format='csr')
    A = sp.kron(I, e) + sp.kron(sp.diags([1], [1], shape=(n, n), format='csr'), -I) + sp.kron(sp.diags([1], [-1], shape=(n, n), format='csr'), -I)
    A = A.toarray()
    return A