# -*- coding: utf-8 -*-

"""
Métodos Numéricos - Análisis numérico 
Universidad Nacional de Colombia, sede Medellín
Marzo 2025 

@Autores: Mauricio Osorio

Animación del comportamiento del método de bisección.

Parámetros:
- f: función (pasar como lambda o función)
- a: límite inferior del intervalo
- b: límite superior del intervalo
- delta: tolerancia

Retorna:
- c: aproximación del cero de la función

"""


import numpy as np
import matplotlib.pyplot as plt
import time
from tkinter import Tk, messagebox

def animacion_biseccion(f, a, b, delta):
   

    ya = f(a)
    yb = f(b)

    if ya * yb > 0:
        Tk().withdraw()
        messagebox.showerror("Error", "La función tiene el mismo signo en a y en b: f(a)*f(b) > 0")
        return None

    max_iter = 1 + round((np.log(b - a) - np.log(delta)) / np.log(2))

    # Preparar gráfico
    plt.ion()
    fig, ax = plt.subplots()
    x_vals = np.linspace(0.1 * round(10 * a - 1), 0.1 * round(10 * b + 1), 400)
    y_vals = f(x_vals)
    ax.plot(x_vals, y_vals, 'g', label='función f(x)')
    ax.axhline(0, color='b', linestyle='-', label='recta y=0')
    ax.grid(True)
    
    Tk().withdraw()
    messagebox.showwarning("Instrucción", "Presiona OK para empezar la animación.\nNo cierres la ventana hasta que finalice.")

    c = (a + b) / 2
    ap, = ax.plot([a, a], [0, f(a)], '--ks', label='a_k')
    bp, = ax.plot([b, b], [0, f(b)], '--kd', label='b_k')
    cp, = ax.plot([c, c], [0, f(c)], '--ro', label='c_k')
    ax.legend(loc='best')

    for k in range(1, max_iter + 1):
        c = (a + b) / 2
        yc = f(c)

        time.sleep(0.5)
        ap.set_xdata([a, a])
        ap.set_ydata([0, f(a)])
        
        bp.set_xdata([b, b])
        bp.set_ydata([0, f(b)])
        time.sleep(0.7)

        cp.set_xdata([c, c])
        cp.set_ydata([0, f(c)])
        time.sleep(0.5)

        if yc == 0:
            a = b = c
        elif yb * yc > 0:
            b = c
            yb = yc
        else:
            a = c
            ya = yc

        ax.set_xlabel(f"Aproximación al cero de f(x), c({k}) = {c:.6f}")
        plt.pause(0.01)

        if abs(b - a) < delta:
            break

    c = (a + b) / 2
    time.sleep(0.5)
    ap.set_xdata([a, a])
    ap.set_ydata([0, f(a)])
    
    bp.set_xdata([b, b])
    bp.set_ydata([0, f(b)])
    time.sleep(0.5)
    
    cp.set_xdata([c, c])
    cp.set_ydata([0, f(c)])
    
    plt.ioff()
    plt.show()

    return c

# ejemplo de uso:
    
# Función ejemplo
f = lambda x: x**3 - x - 2

# Ejecutar animación de bisección
cero_aprox = animacion_biseccion(f, 1, 2, 1e-4)
print(f"Aproximación del cero: {cero_aprox}")
