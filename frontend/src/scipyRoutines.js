// Rutinas de numpy/scipy/scikit-learn para autocompletar en la celda de código.
// Reemplaza las rutinas propias del curso (Rutinas_MN_Python_Est): los problemas
// generados por el pipeline de agentes IA exigen resolver con la biblioteca real,
// no con una implementación manual del método (ver gemini_agents.py,
// SUPPORTED_METHODS_TABLE). Nombres verificados contra las versiones instaladas
// (scipy 1.18, numpy 2.5, scikit-learn 1.9) — p.ej. numpy.trapz y
// scipy.integrate.simps ya no existen en estas versiones, por eso no aparecen
// aquí aunque sean comunes en tutoriales viejos.
//
// Métodos SIN rutina real en estas bibliotecas (Jacobi, Gauss-Seidel, SOR;
// Euler/Taylor/Runge-Kutta de paso fijo para PVI) no están en esta lista a
// propósito: el pipeline de agentes tampoco genera problemas para esos métodos.
export const SCIPY_ROUTINES = [
  // Raíces
  { module: 'scipy.optimize', func: 'bisect', args: 'f, a, b', desc: 'Bisección: encuentra una raíz de f en el intervalo [a, b].' },
  { module: 'scipy.optimize', func: 'fixed_point', args: 'func, x0', desc: 'Punto fijo: encuentra x tal que func(x) = x, partiendo de x0.' },
  { module: 'scipy.optimize', func: 'newton', args: 'func, x0, fprime=None, fprime2=None', desc: 'Newton-Raphson (con fprime); Newton modificado si además se da fprime2.' },

  // Sistemas de ecuaciones no lineales (Newton para sistemas, dado el jacobiano)
  { module: 'scipy.optimize', func: 'fsolve', args: 'func, x0, fprime=None', desc: 'Newton para sistemas de ecuaciones no lineales (pasar el jacobiano en fprime).' },
  { module: 'scipy.optimize', func: 'root', args: 'fun, x0, jac=None, method="hybr"', desc: 'Alternativa a fsolve; con jac=jacobiano y method="hybr" se comporta como Newton para sistemas.' },

  // Interpolación
  { module: 'scipy.interpolate', func: 'lagrange', args: 'x, w', desc: 'Polinomio interpolante de Lagrange para los puntos (x, w).' },
  { module: 'scipy.interpolate', func: 'KroghInterpolator', args: 'xi, yi', desc: 'Interpolación por diferencias divididas de Newton.' },
  { module: 'numpy.polynomial.chebyshev', func: 'chebpts1', args: 'npts', desc: 'Nodos de Chebyshev de primera especie en [-1, 1].' },
  { module: 'numpy.polynomial.chebyshev', func: 'chebpts2', args: 'npts', desc: 'Nodos de Chebyshev de segunda especie (incluye los extremos) en [-1, 1].' },
  { module: 'scipy.interpolate', func: 'CubicSpline', args: 'x, y, bc_type="not-a-knot"', desc: 'Spline cúbico que interpola los puntos (x, y).' },

  // Regresión lineal
  { module: 'numpy', func: 'polyfit', args: 'x, y, deg', desc: 'Ajusta un polinomio de grado `deg` (deg=1 para regresión lineal simple).' },
  { module: 'numpy.linalg', func: 'lstsq', args: 'A, b, rcond=None', desc: 'Mínimos cuadrados: resuelve Ax ≈ b.' },
  { module: 'scipy.stats', func: 'linregress', args: 'x, y', desc: 'Regresión lineal simple: pendiente, intercepto, r, p-valor, error estándar.' },
  { module: 'sklearn.linear_model', func: 'LinearRegression', args: '', desc: 'Regresión lineal (usar .fit(X, y) y luego .coef_/.intercept_).' },

  // Integración
  { module: 'scipy.integrate', func: 'trapezoid', args: 'y, x=None, dx=1.0', desc: 'Regla del Trapecio sobre puntos (x, y) o con espaciamiento dx.' },
  { module: 'scipy.integrate', func: 'simpson', args: 'y, x=None, dx=1.0', desc: 'Regla de Simpson sobre puntos (x, y) o con espaciamiento dx.' },
  { module: 'scipy.integrate', func: 'fixed_quad', args: 'func, a, b, n=5', desc: 'Cuadratura Gaussiana de n nodos fijos en [a, b].' },

  // Ecuaciones diferenciales con valores iniciales (para disparo lineal en PVF)
  { module: 'scipy.integrate', func: 'solve_ivp', args: 'fun, t_span, y0', desc: 'Resuelve un problema de valor inicial (PVI); útil como paso del método de disparo lineal.' },

  // PVF: diferencias finitas
  { module: 'scipy.linalg', func: 'solve_banded', args: 'l_and_u, ab, b', desc: 'Resuelve un sistema lineal en forma de banda (p.ej. el sistema tridiagonal de diferencias finitas).' },
  { module: 'numpy.linalg', func: 'solve', args: 'a, b', desc: 'Resuelve el sistema lineal Ax = b.' },
];
