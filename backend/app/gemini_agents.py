"""Pipeline de 4 agentes (Gemini vía Google AI Studio) para cargar problemas
a un banco a partir de un archivo .tex:

  Agente 1 (agent1_parse_tex): lee el .tex y lo adapta a N problemas de
  programación viables para el sitio (enunciado + starter_code + variables
  finales a revisar), capturando también el fragmento original (source_excerpt)
  y la respuesta de referencia del .tex si la trae (reference_answer). El
  enunciado SÍ nombra el método/algoritmo numérico a usar (y sus parámetros,
  p.ej. número de nodos/subintervalos) — lo que NUNCA revela es la rutina
  concreta de scipy/numpy/scikit-learn que lo implementa; el estudiante debe
  reconocerla y usarla (está PROHIBIDO programar el método a mano: la
  resolución debe apoyarse en las rutinas de esas bibliotecas), como parte
  de lo que se evalúa.

  Agente 2 (agent2_generate_solution): escribe una solución de referencia en
  Python usando numpy/scipy/scikit-learn para cada problema, resolviéndolo
  con la rutina de esas bibliotecas que implementa el método que pide el
  enunciado (nunca programando el método a mano).

  Agente 3 (agent3_propose_rubric + build_and_validate_rubric): propone la
  rúbrica y la VALIDA de verdad ejecutando la solución de referencia contra
  el motor de calificación real (executor.py) — el valor "expected" de cada
  chequeo final_value nunca se toma de lo que dice el LLM, sino del valor que
  realmente produce la solución de referencia al ejecutarla. La rúbrica no
  solo revisa el resultado final: también evalúa el PROCEDIMIENTO (checks
  "function" — definir correctamente la función matemática del problema — y
  "call" — usar la rutina numérica correcta), cada uno agregado solo si no
  rompe la validación 100/100 (se descarta en silencio si no).

  Agente 4 (agent4_audit + check_reference_answer): audita el resultado —
  compara el valor calculado contra la respuesta de referencia del .tex
  original si la hay (chequeo numérico, sin LLM) y revisa fidelidad/claridad
  del enunciado adaptado (auditoría cualitativa, con LLM). Nunca bloquea la
  creación del problema; solo deja una nota (Problem.review_notes) para que
  el docente la lea al revisar el borrador.

  Los problemas se guardan con status="draft" (ver orchestrate_load_tex)
  para revisión humana antes de publicarse.
"""
import json
import os
import re
import time
from collections.abc import Callable

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from . import executor, models
from .gemini_quota import check_and_reserve, record_tokens, QuotaExceededError

load_dotenv(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env")))

RETRYABLE_STATUS_CODES = {429, 500, 503}
MAX_TRANSIENT_RETRIES = 3


# ---------------------------------------------------------------------------
# Schemas de salida estructurada. Pasarle response_schema a la API (no solo
# response_mime_type="application/json") fuerza decodificación restringida
# de verdad: sin esto, el modelo a veces deja backslashes de LaTeX sin
# escapar dentro de los strings del JSON (p.ej. "\int" en vez de "\\int") y
# el JSON queda inválido de forma intermitente.
# ---------------------------------------------------------------------------


class _VariableSpec(BaseModel):
    name: str
    description: str
    suggested_points: float
    # True si el valor final esperado es un vector o una matriz (p.ej. la
    # solución de un sistema lineal, o una matriz de iteración de Jacobi/
    # Gauss-Seidel/SOR) en vez de un número suelto. build_and_validate_rubric
    # compara estas variable por componente (ver executor._values_close), en
    # vez de forzarlas a float().
    is_matrix: bool = False


class _ProblemDraft(BaseModel):
    title: str
    statement_md: str
    starter_code: str
    variables_to_check: list[_VariableSpec]
    source_excerpt: str
    # Respuesta numérica de referencia del .tex original, si la trae (p.ej.
    # el valor final de un check "numerical" de un quiz Moodle cloze), y a
    # cuál de variables_to_check corresponde. Sirve para el chequeo de
    # auditoría numérica en build_and_validate_rubric — NUNCA se usa como
    # "expected" real de la rúbrica (eso siempre sale de ejecutar la
    # solución del agente 2).
    reference_answer: float | None = None
    reference_variable: str | None = None
    # True si el enunciado original pide explícitamente graficar (p.ej.
    # "grafique f y determine cuántos ceros tiene") — agrega un check "plot"
    # (¿el estudiante dejó al menos una figura de matplotlib abierta?) a la
    # rúbrica. No compara la gráfica contra una referencia, solo que exista.
    requires_plot: bool = False


class _SkippedExercise(BaseModel):
    title: str
    reason: str


class _Agent1Output(BaseModel):
    problems: list[_ProblemDraft]
    # Numerales que el .tex pedía resolver con un método SIN rutina real de
    # numpy/scipy/scikit-learn (ver lista de métodos soportados en
    # AGENT1_SYSTEM) — se omiten en vez de forzar una rutina que no
    # corresponde al método pedido.
    skipped: list[_SkippedExercise] = []


class _CallCheckSpec(BaseModel):
    label: str
    qualname: str
    points: float


class _FunctionCheckSpec(BaseModel):
    label: str
    arg_names: list[str]
    ref_body: str  # expresión Python (usa arg_names) equivalente a la función de la solución
    test_points: list[list[float]]  # puntos donde probar esa función, uno por argumento
    points: float


class _VariablePoints(BaseModel):
    name: str
    points: float


class _Agent3Output(BaseModel):
    final_value_points: list[_VariablePoints]
    function_checks: list[_FunctionCheckSpec]
    call_checks: list[_CallCheckSpec]
    # Rutinas alternativas que resolverían el problema COMPLETO sin pasar por
    # el método que pide el enunciado (p.ej. si se exige bisect, bloquear
    # brentq/fsolve/sympy.nsolve) — se deshabilitan (lanzan RuntimeError si se
    # llaman) para que "llamar la rutina exigida de adorno y calcular la
    # respuesta real por otro camino" ya no pueda dar el puntaje completo.
    # NUNCA incluir aquí sympy.lambdify ni sympy.diff/factor/simplify: son
    # pasos analíticos legítimos, no atajos numéricos.
    blocked_qualnames: list[str] = []


class _Agent4Output(BaseModel):
    severity: str  # "ok" | "low" | "high"
    summary: str
    concerns: list[str]


_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY no configurada (backend/.env).")
        _client = genai.Client(api_key=api_key)
    return _client


def _model() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")


def _call_gemini(prompt: str, system: str, response_schema: type[BaseModel] | None = None):
    """Devuelve el objeto respuesta completo. Si se pasa response_schema, la
    API usa decodificación restringida por ese esquema (más confiable que
    solo pedir JSON por instrucción: garantiza escapes válidos incluso con
    contenido LaTeX lleno de backslashes) y `resp.parsed` trae ya la
    instancia validada de ese modelo Pydantic."""
    config_kwargs = {"system_instruction": system}
    if response_schema is not None:
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = response_schema

    last_error = None
    for attempt in range(MAX_TRANSIENT_RETRIES + 1):
        check_and_reserve()
        client = _get_client()
        try:
            resp = client.models.generate_content(
                model=_model(),
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            break
        except genai_errors.APIError as e:
            last_error = e
            if getattr(e, "code", None) in RETRYABLE_STATUS_CODES and attempt < MAX_TRANSIENT_RETRIES:
                time.sleep(2**attempt)
                continue
            raise
    else:
        raise last_error

    if resp.usage_metadata and resp.usage_metadata.total_token_count:
        record_tokens(resp.usage_metadata.total_token_count)
    if response_schema is not None:
        if resp.parsed is None:
            raise RuntimeError("Gemini no devolvió contenido válido según el esquema esperado.")
        return resp.parsed
    if not resp.text:
        raise RuntimeError("Gemini no devolvió contenido (posible bloqueo de seguridad del prompt).")
    return resp.text


def _strip_fence(text: str, lang: str = "") -> str:
    cleaned = text.strip()
    cleaned = re.sub(rf"^```(?:{lang})?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned


# ---------------------------------------------------------------------------
# Tabla de métodos soportados: para cada método que puede pedir un enunciado,
# la rutina REAL de numpy/scipy/scikit-learn que lo implementa (verificada
# contra las versiones instaladas: scipy 1.18, numpy 2.5, scikit-learn 1.9 —
# p.ej. numpy.trapz y scipy.integrate.simps ya no existen en estas versiones,
# por eso NO aparecen aquí aunque sean comunes en tutoriales viejos). Un
# problema solo se genera si su método está en esta lista; si el .tex pide un
# método que no tiene rutina real (ver "NO soportados"), el agente 1 omite
# ese numeral en vez de forzar una rutina que no corresponde al método
# pedido. Se usa tanto en AGENT1_SYSTEM (para decidir qué omitir) como en
# AGENT2_SYSTEM (para que la solución de referencia use el nombre exacto de
# la rutina, sin inventarlo).
# ---------------------------------------------------------------------------

SUPPORTED_METHODS_TABLE = """MÉTODOS SOPORTADOS (con su rutina real de numpy/scipy/scikit-learn):
- Raíces:
  - Bisección -> scipy.optimize.bisect
  - Punto fijo -> scipy.optimize.fixed_point
  - Newton (Newton-Raphson) -> scipy.optimize.newton (con el argumento fprime)
  - Newton modificado (para raíces de multiplicidad >1) -> scipy.optimize.newton (con fprime y fprime2)
- Sistemas de ecuaciones NO lineales:
  - Newton para sistemas (dado el jacobiano) -> scipy.optimize.fsolve (con fprime=jacobiano) o scipy.optimize.root(..., jac=jacobiano, method="hybr")
- Sistemas de ecuaciones lineales:
  - Solución directa -> scipy.linalg.solve
  - Jacobi / Gauss-Seidel / SOR -> SOLO se pregunta por su MATRIZ DE ITERACIÓN T (no hay rutina de \
scipy que itere con estos métodos: scipy solo trae solvers de Krylov como cg/gmres, que son \
algoritmos distintos). No generes un problema que pida "resuelva el sistema iterando con Jacobi/GS/ \
SOR" ni que pida contar iteraciones de convergencia de estos métodos — eso sigue sin tener rutina \
real. Sí se puede pedir "construya y reporte la matriz de iteración T de Jacobi/Gauss-Seidel/SOR", \
calculada con numpy a partir de la descomposición A=D-L-U (D diagonal, L y U triangulares con signo \
negativo): T_jacobi = D⁻¹(L+U); T_gauss_seidel = (D-L)⁻¹U; T_sor = (D-ωL)⁻¹((1-ω)D+ωU). Esa variable \
es una matriz (is_matrix=true en variables_to_check), no hay una única "rutina" que llamar (se \
construye con numpy.diag/tril/triu/linalg.inv), así que estos problemas pueden llevar call_checks \
vacío si de verdad no hay una llamada identificable — no fuerces uno.
- Interpolación:
  - Lagrange -> scipy.interpolate.lagrange
  - Diferencias divididas de Newton -> scipy.interpolate.KroghInterpolator
  - Nodos de Chebyshev -> numpy.polynomial.chebyshev.chebpts1 o chebpts2
  - Splines cúbicos -> scipy.interpolate.CubicSpline
- Regresión lineal -> numpy.polyfit, numpy.linalg.lstsq, scipy.stats.linregress, o sklearn.linear_model.LinearRegression
- Integración:
  - Trapecio -> scipy.integrate.trapezoid
  - Simpson -> scipy.integrate.simpson
  - Cuadratura Gaussiana de N nodos -> scipy.integrate.fixed_quad (parámetro n=N)
- Ecuaciones diferenciales con valores de frontera (PVF):
  - Disparo lineal -> scipy.integrate.solve_ivp (se llama dos veces y se combinan linealmente los resultados; el problema es lineal así que no hace falta buscar raíz)
  - Diferencias finitas -> construir el sistema tridiagonal/banda a mano y resolverlo con scipy.linalg.solve_banded o numpy.linalg.solve

MÉTODOS NO SOPORTADOS (sin rutina real en numpy/scipy/scikit-learn — NUNCA generes un problema para un numeral que pida alguno de estos; ver regla de omisión):
- Jacobi, Gauss-Seidel, SOR pidiendo RESOLVER el sistema iterando (contar iteraciones, ver convergencia, obtener la solución x) — sin rutina real; solo su matriz de iteración T es calificable (ver arriba).
- Ecuaciones diferenciales con valores iniciales (PVI), individuales o en sistemas, con método de PASO FIJO: Euler, Euler modificado, Taylor, Runge-Kutta de orden 2/3/4 clásico. scipy.integrate.solve_ivp solo implementa métodos ADAPTATIVOS (RK45, RK23, etc.), no estos de paso fijo h constante que pide el enunciado."""


# ---------------------------------------------------------------------------
# Agente 1: .tex -> problemas de programación viables
# ---------------------------------------------------------------------------

AGENT1_SYSTEM = """Eres un asistente que convierte enunciados de examen en LaTeX (a veces en \
formato de quiz Moodle con variantes numéricas tipo "cloze") en problemas de programación \
viables para una plataforma donde el estudiante escribe código Python, lo ejecuta, y se \
califica automáticamente revisando el valor final de ciertas variables.

Reglas:
- Cada ejercicio numerado del .tex (numeral, p.ej. "1.", "2.", "Ejercicio 3") se convierte en UN \
SOLO problema. PROHIBIDO dividir un mismo numeral en varios problemas: si trae varios sub-incisos \
(a), b), c)...) o pide varias cantidades/resultados, van TODOS dentro del MISMO problema, como \
entradas distintas de variables_to_check (una por cada resultado pedido), no como problemas \
separados.
- Excepción: si el .tex usa el formato Moodle cloze con variantes numéricas independientes de UN \
mismo numeral (mismo enunciado, distintos parámetros, pensado para sortear aleatoriamente entre \
estudiantes), cada variante sí se convierte en un problema aparte — porque son sorteos de LA MISMA \
pregunta para distintos estudiantes, no sub-partes de ella. No confundas esto con dividir un \
numeral por sus incisos.
- El enunciado adaptado (statement_md) debe:
  - Estar en Markdown, con fórmulas LaTeX usando $...$ o $$...$$ (compatible con KaTeX).
  - Explicar el contexto matemático y pedir explícitamente escribir código Python que resuelva \
el problema usando las rutinas de numpy/scipy/scikit-learn correspondientes al método pedido \
(no pedir solo "la respuesta numérica", y aclarar que no se debe programar el método a mano).
  - Terminar con una sección "### Calificación (100 puntos)" listando qué se evalúa y sus puntos, \
SIN mencionar en esa lista qué rutina específica de scipy/numpy/sklearn se usa (ver regla siguiente) \
— solo qué variables o comportamiento se revisa (p.ej. "20 pts — definir correctamente la función", \
"30 pts — valor final correcto", "20 pts — usar la rutina numérica apropiada para el método pedido").
  - Mencionar los nombres EXACTOS de las variables donde debe guardarse cada resultado (deben \
coincidir con starter_code y variables_to_check).
- requires_plot: true si el enunciado original pide explícitamente graficar (p.ej. "grafique f en \
[a,b]", "muestre gráficamente que..."), aunque sea como paso previo a otra pregunta (p.ej. "grafique \
f y determine cuántos ceros tiene"). No lo marques true solo porque graficar ayudaría; solo si el \
enunciado lo pide con esas palabras.
- "Determine cuántos ceros/raíces/puntos fijos tiene f" (sin pedir localizarlos todos con el método \
numérico) SÍ es una pregunta legítima con resultado numérico: agrega una variable_to_check tipo \
"numero_de_raices" (un entero) — el agente 2 la calculará escaneando la función, no hace falta que \
el enunciado revele cómo contar.
- Una variable cuyo valor esperado es un vector o una matriz (la solución de un sistema, una matriz \
de iteración de Jacobi/Gauss-Seidel/SOR, etc.) lleva is_matrix=true en variables_to_check y su \
description debe decir la forma esperada (p.ej. "vector de 3 componentes", "matriz 3x3").
- sympy SÍ está disponible para el estudiante como herramienta de pasos analíticos (derivar, \
factorizar, simplificar, y luego sympy.lambdify para volver la expresión numérica) — esto no es un \
atajo para resolver el problema, así que puede mencionarse en el enunciado como una forma válida de \
llegar a definir la función que luego se le pasa al método numérico exigido. No la reveles como LA \
forma de resolver el problema completo (el método numérico exigido sigue siendo obligatorio).
- El enunciado SÍ debe decir explícitamente qué método/algoritmo numérico usar y sus parámetros \
(p.ej. "usa la regla de Simpson con 140 subintervalos", "resuelve con Runge-Kutta de orden 4", \
"usa cuadratura Gaussiana con 3 nodos", "usa el método de disparo") — eso no es lo que se evalúa, \
es un dato del enunciado como cualquier otro.
- PROHIBIDO revelar la rutina concreta de scipy/numpy/scikit-learn que resuelve el problema: nunca \
nombres ni insinúes la función a importar/llamar (p.ej. no digas "usa scipy.integrate.quad" ni \
"usa numpy.linalg.solve" ni "usa scipy.integrate.solve_ivp"). Describe el método pedido y el \
problema matemático (la integral, la EDO, el sistema, la interpolación, etc.), sus datos y qué \
variables debe producir el código — el estudiante debe reconocer, dado el método pedido, qué \
rutina de numpy/scipy/scikit-learn lo implementa y usarla; PROHIBIDO que el problema se pueda \
resolver programando el método a mano (sin rutina de biblioteca) — debe existir una rutina real \
de esas bibliotecas que lo resuelva directamente. starter_code tampoco debe traer imports que ya \
insinúen esa rutina (ver regla de starter_code abajo).
- starter_code declara esas variables como None con un comentario "# No modificar el nombre de \
esta variable", nada más (no debe resolver el problema, ni incluir imports que ya delaten qué \
función de scipy/numpy/sklearn hay que usar).
- No copies literalmente una respuesta numérica de referencia del .tex al enunciado (el sistema \
recalculará el valor correcto con su propia solución de referencia).
- source_excerpt: copia el fragmento EXACTO del .tex original (el bloque cloze/pregunta) del que \
sale este problema — se usa después para auditar que la adaptación fue fiel al original.
- reference_answer / reference_variable: si el .tex trae una respuesta numérica de referencia \
para este problema (p.ej. un \\item con un valor, o un tag [tolerance=...] seguido de un número), \
repórtala en reference_answer y di en reference_variable cuál de variables_to_check le \
corresponde. Si el .tex no trae ninguna respuesta de referencia, deja ambos en null.
- OBLIGATORIO: el método que pide cada numeral debe estar en la lista de MÉTODOS SOPORTADOS de \
abajo (tiene rutina real de numpy/scipy/scikit-learn). Si un numeral pide un método de la lista \
MÉTODOS NO SOPORTADOS (o cualquier otro sin rutina real conocida), NO generes un problema para \
ese numeral — repórtalo en "skipped" con su título/tema y una razón breve (p.ej. "pide método de \
Jacobi, sin rutina real en numpy/scipy/sklearn"), y sigue con el resto de numerales normalmente.

""" + SUPPORTED_METHODS_TABLE + """

- Responde ÚNICAMENTE con JSON válido (sin markdown, sin explicación), exactamente con esta forma:
{
  "problems": [
    {
      "title": "string corto",
      "statement_md": "string en markdown",
      "starter_code": "string de código python",
      "variables_to_check": [
        {"name": "nombre_variable", "description": "qué debe contener", "suggested_points": 20}
      ],
      "source_excerpt": "fragmento exacto del .tex original",
      "reference_answer": 1.422,
      "reference_variable": "nombre_variable"
    }
  ],
  "skipped": [
    {"title": "string corto del numeral omitido", "reason": "por qué se omitió"}
  ]
}"""


AGENT1_BATCH_SIZE = int(os.environ.get("GEMINI_AGENT1_BATCH_SIZE", "4"))

_CLOZE_BLOCK_RE = re.compile(r"\\begin\{cloze\}.*?\\end\{cloze\}", re.DOTALL)
_ENV_TOKEN_RE = re.compile(r"\\begin\{([a-zA-Z*]+)\}|\\end\{([a-zA-Z*]+)\}|\\item\b")


def _identity_wrap(body: str) -> str:
    return body


def _enumerate_wrap(body: str) -> str:
    return "\\begin{enumerate}\n" + body + "\n\\end{enumerate}\n"


def _split_cloze_blocks(tex_source: str) -> tuple[str, list[str], Callable[[str], str]] | None:
    """Formato Moodle cloze: un bloque \\begin{cloze}...\\end{cloze} por numeral."""
    blocks = _CLOZE_BLOCK_RE.findall(tex_source)
    if len(blocks) < 2:
        return None
    preamble = tex_source[: tex_source.index(blocks[0])]
    return preamble, blocks, _identity_wrap


def _split_plain_enumerate(tex_source: str) -> tuple[str, list[str], Callable[[str], str]] | None:
    """.tex "normal" (no Moodle cloze): un \\begin{enumerate}...\\end{enumerate} de
    nivel superior con un \\item por ejercicio. Encuentra el primer enumerate que no
    esté anidado dentro de otro entorno, y lo corta por cada \\item que esté
    DIRECTAMENTE en ese nivel (no dentro de un enumerate/itemize anidado, p.ej. los
    incisos a), b), c) de un mismo ejercicio, que no cuentan como ejercicios nuevos).
    Devuelve None si no encuentra un enumerate de nivel superior con al menos 2 \\item
    directos (.tex sin ese formato, o con un solo ejercicio)."""
    start_match = re.search(r"\\begin\{enumerate\}", tex_source)
    if not start_match:
        return None
    preamble = tex_source[: start_match.start()]

    depth = 1
    pos = start_match.end()
    item_starts: list[int] = []
    enum_end = None
    for m in _ENV_TOKEN_RE.finditer(tex_source, pos):
        if m.group(1):  # \begin{...}
            depth += 1
        elif m.group(2):  # \end{...}
            depth -= 1
            if depth == 0:
                enum_end = m.end()
                break
        elif depth == 1:  # \item directo en este enumerate
            item_starts.append(m.start())

    if enum_end is None or len(item_starts) < 2:
        return None

    boundaries = item_starts + [enum_end - len(r"\end{enumerate}")]
    bodies = [tex_source[boundaries[i] : boundaries[i + 1]] for i in range(len(item_starts))]
    return preamble, bodies, _enumerate_wrap


def _split_tex_into_batches(tex_source: str, batch_size: int) -> list[str] | None:
    """Parte el .tex en lotes de a lo sumo `batch_size` ejercicios/numerales por
    llamada al agente 1 (probando los formatos soportados en orden: Moodle cloze,
    luego enumerate con nivel superior), cada lote con el preámbulo puesto UNA sola
    vez (no uno por ejercicio, para no inflar tokens). Mandarle al agente 1 todo el
    .tex de una sola vez cuando trae muchos ejercicios le hace mezclar/alucinar datos
    entre ellos con más frecuencia; en lotes chicos es más confiable. Devuelve None si
    ningún formato aplica (.tex con un formato distinto, o con un solo ejercicio) —
    en ese caso el llamador manda el archivo completo tal cual, como antes."""
    split = _split_cloze_blocks(tex_source) or _split_plain_enumerate(tex_source)
    if split is None:
        return None
    preamble, bodies, wrap = split
    return [
        preamble + wrap("\n\n".join(bodies[i : i + batch_size]))
        for i in range(0, len(bodies), batch_size)
    ]


def agent1_parse_tex(tex_source: str, max_problems: int | None = None) -> tuple[list[dict], list[dict]]:
    """Devuelve (problems, skipped). `skipped` son numerales que el agente 1
    decidió NO convertir en problema porque el método que piden no tiene una
    rutina real de numpy/scipy/scikit-learn (ver SUPPORTED_METHODS_TABLE) —
    p.ej. Jacobi/Gauss-Seidel/SOR, o Euler/Taylor/Runge-Kutta de paso fijo."""
    batches = _split_tex_into_batches(tex_source, AGENT1_BATCH_SIZE) or [tex_source]

    problems: list[dict] = []
    skipped: list[dict] = []
    for batch in batches:
        if max_problems is not None and len(problems) >= max_problems:
            break
        prompt = f"Convierte el siguiente archivo .tex en problemas de programación:\n\n{batch}"
        if max_problems is not None:
            remaining = max_problems - len(problems)
            prompt += f"\n\nGenera como máximo {remaining} problema(s) (los más representativos si hay más variantes)."
        parsed: _Agent1Output = _call_gemini(prompt, AGENT1_SYSTEM, response_schema=_Agent1Output)
        problems.extend(p.model_dump() for p in parsed.problems)
        skipped.extend(s.model_dump() for s in parsed.skipped)

    if not problems and not skipped:
        raise RuntimeError("el agente 1 no extrajo ningún problema del .tex")
    return (problems[:max_problems] if max_problems else problems), skipped


# ---------------------------------------------------------------------------
# Agente 2: solución de referencia con numpy/scipy/sklearn
# ---------------------------------------------------------------------------

AGENT2_SYSTEM = """Eres un experto en métodos numéricos con Python. Recibes el enunciado de un \
problema (que nombra el método numérico a usar) y la lista de variables que se deben calcular. \
Escribe una ÚNICA solución de referencia en Python usando numpy, scipy y/o scikit-learn \
(bibliotecas estándar, no rutinas de un curso en particular) que calcule esas variables \
correctamente.

Reglas:
- OBLIGATORIO resolver el problema llamando la rutina de numpy/scipy/scikit-learn que implementa \
el método que pide el enunciado — PROHIBIDO programar el método a mano (p.ej. escribir tú mismo el \
bucle de Runge-Kutta o la suma de Simpson en vez de llamar la rutina de la biblioteca que lo hace). \
Usa el nombre EXACTO de la rutina según el método pedido, de esta tabla (no inventes otro nombre \
ni uses una función que no exista en estas bibliotecas):

""" + SUPPORTED_METHODS_TABLE + """

- sympy está disponible y es una forma válida de llegar a la función que se le pasa al método \
numérico exigido: puedes definir la expresión simbólicamente (derivar, factorizar, simplificar con \
sympy) y convertirla a una función numérica con sympy.lambdify(variable, expr, "numpy") antes de \
pasarla a la rutina de scipy exigida. sympy NUNCA reemplaza esa rutina (nunca uses sympy.solve ni \
sympy.nsolve como LA forma de resolver el problema; solo como paso previo para definir la función).
- Si una variable pedida es "número de raíces/ceros/puntos fijos" (un conteo, no la lista de \
valores), calcúlalo escaneando la función en una malla fina del dominio dado (p.ej. \
`np.linspace(a, b, 2000)`) y contando cambios de signo consecutivos de f (para raíces) o de g(x)-x \
(para puntos fijos de g) — NO uses una rutina de biblioteca para esto, es una cuenta directa.
- Si una variable pedida es una matriz de iteración de Jacobi/Gauss-Seidel/SOR (is_matrix=true), \
constrúyela con numpy a partir de A=D-L-U, usando EXACTAMENTE estas fórmulas (D=np.diag(np.diag(A)), \
L=-np.tril(A,-1), U=-np.triu(A,1)): T_jacobi = np.linalg.inv(D) @ (L+U); \
T_gauss_seidel = np.linalg.inv(D-L) @ U; T_sor = np.linalg.inv(D-omega*L) @ ((1-omega)*D+omega*U). No \
inventes otra convención de signos para L/U: con esta, A = D-L-U y las fórmulas de arriba son las \
matrices de iteración estándar.
- Si el problema tiene requires_plot=true, incluye también código que genere al menos una figura de \
matplotlib (`import matplotlib.pyplot as plt; plt.plot(...)`) de la función relevante — no hace \
falta llamar a plt.show() ni cerrarla.
- El código debe ser autocontenido: incluye todos los imports que uses.
- Debe definir EXACTAMENTE las variables pedidas, con esos mismos nombres. Una variable normal debe \
ser un valor numérico (float o algo convertible a float con float(...)); una variable con \
is_matrix=true debe ser un numpy.ndarray (vector o matriz) o una lista anidada de números.
- No debe leer archivos, pedir input(), ni imprimir nada imprescindible para el resultado.
- Responde ÚNICAMENTE con el código Python, sin explicación y sin bloques de markdown."""


def agent2_generate_solution(problem: dict, previous_error: str | None = None) -> str:
    prompt = (
        f"Enunciado:\n{problem['statement_md']}\n\n"
        f"Código inicial (variables a definir):\n{problem['starter_code']}\n\n"
        f"Variables a calcular: {json.dumps(problem['variables_to_check'], ensure_ascii=False)}\n\n"
        f"requires_plot: {problem.get('requires_plot', False)}"
    )
    if previous_error:
        prompt += f"\n\nUn intento anterior falló al ejecutarse con este error; corrígelo:\n{previous_error}"
    return _strip_fence(_call_gemini(prompt, AGENT2_SYSTEM), "python")


# ---------------------------------------------------------------------------
# Agente 3: propuesta de rúbrica + validación real contra el executor
# ---------------------------------------------------------------------------

AGENT3_SYSTEM = """Eres un asistente que diseña rúbricas de calificación automática para \
problemas de programación en métodos numéricos. Recibes el enunciado (que SÍ nombra el método \
esperado, pero NUNCA la rutina concreta de scipy/numpy/sklearn que lo implementa), las variables \
finales a revisar, y una solución de referencia. La calificación no debe premiar solo "adivinar" \
el número final: también debe evaluar el PROCEDIMIENTO — que el estudiante haya escrito \
correctamente la función/modelo matemático del problema y/o haya reconocido y usado la rutina de \
scipy/numpy/sklearn que implementa el método pedido — igual que revisaría a mano un profesor.

Debes proponer TRES tipos de chequeo:

1. "final_value_points": puntos de cada variable final (ver lista de variables a revisar). Esta \
parte es la red de seguridad: si el estudiante resuelve bien el problema por un camino numérico \
válido distinto al de la solución de referencia, esto igual le da la mayoría del puntaje.

2. "function_checks": OBLIGATORIO al menos 1 (hasta 2) si la solución de referencia define una \
función matemática central para resolver el problema (el integrando, el lado derecho de una EDO, \
el residuo de un sistema, etc.) — verifica que el estudiante haya definido esa función \
correctamente, SIN exigir un nombre de variable específico (se busca por comportamiento numérico, \
no por nombre). Para cada una da: arg_names (nombres de los argumentos, en el mismo orden que la \
función de la solución), ref_body (una expresión Python, usando esos arg_names, matemáticamente \
equivalente al cuerpo de esa función en la solución de referencia — debe poder evaluarse con \
`eval()` usando solo esos nombres y funciones de math/numpy), y test_points (4-8 puntos donde \
probarla, cada uno una lista con un valor por argumento).

3. "call_checks": la solución de referencia debe llamar una función concreta de numpy/scipy/sklearn \
que implemente el método numérico pedido (p.ej. "scipy.integrate.quad", "scipy.optimize.brentq", \
"numpy.linalg.solve", "scipy.integrate.solve_ivp"); da su nombre calificado EXACTO tal como aparece \
importado/llamado en la solución. OBLIGATORIO al menos 1 (hasta 2), EXCEPTO cuando el problema pide \
construir una matriz de iteración de Jacobi/Gauss-Seidel/SOR: ahí se construye con numpy.diag/tril/ \
triu/linalg.inv (no hay una única rutina que la resuelva), así que call_checks puede ir vacío.

4. "blocked_qualnames": rutinas que, si el estudiante las llama, resolverían el problema COMPLETO \
sin usar el método que pide el enunciado — deshabilítalas (el estudiante ve un error si las llama) \
para que "llamar la rutina exigida una vez, de adorno, y calcular la respuesta real por otro camino" \
ya no dé puntaje completo. Guíate por el método pedido:
   - Si se exige bisección: bloquea scipy.optimize.brentq, scipy.optimize.newton, \
scipy.optimize.fsolve, scipy.optimize.root_scalar, scipy.optimize.ridder, sympy.nsolve, sympy.solve.
   - Si se exige punto fijo (fixed_point): bloquea scipy.optimize.bisect, scipy.optimize.brentq, \
scipy.optimize.fsolve, scipy.optimize.newton, sympy.nsolve, sympy.solve — SALVO que el propio \
enunciado pida explícitamente comparar fixed_point con bisect (en ese caso no bloquees bisect).
   - Si se exige un sistema no lineal con Newton/fsolve: bloquea scipy.optimize.root con otro \
método, sympy.solve, sympy.nsolve.
   - Para integración, interpolación, regresión, EDOs o sistemas lineales: normalmente no hace \
falta bloquear nada (no hay una alternativa de una línea que trivialice el problema); deja la lista \
vacía si no la hay.
   - NUNCA bloquees sympy.lambdify, sympy.diff, sympy.factor, sympy.simplify, ni la creación de \
símbolos (sympy.Symbol): son pasos analíticos legítimos, no atajos numéricos.

Si la solución de referencia no define ninguna función matemática propia, function_checks puede ir \
vacía. blocked_qualnames puede ir vacía si de verdad no aplica.

Reparto de puntos sugerido sobre 100: ~55-65% en final_value_points (la respuesta correcta), \
~35-45% repartido entre function_checks y call_checks (el procedimiento). blocked_qualnames no lleva \
puntos propios (es una restricción, no un chequeo puntuado).

Responde ÚNICAMENTE con JSON válido, exactamente con esta forma:
{
  "final_value_points": [{"name": "nombre_variable", "points": 40}],
  "function_checks": [
    {"label": "string", "arg_names": ["x"], "ref_body": "expresión Python en términos de x",
     "test_points": [[0.1], [0.5], [1.0], [2.0]], "points": 20}
  ],
  "call_checks": [
    {"label": "string", "qualname": "modulo.submodulo.funcion", "points": 20}
  ],
  "blocked_qualnames": ["scipy.optimize.brentq", "sympy.nsolve"]
}"""


def agent3_propose_rubric(problem: dict, solution_code: str) -> dict:
    prompt = (
        f"Enunciado:\n{problem['statement_md']}\n\n"
        f"Variables a revisar: {json.dumps(problem['variables_to_check'], ensure_ascii=False)}\n\n"
        f"Solución de referencia:\n{solution_code}"
    )
    parsed: _Agent3Output = _call_gemini(prompt, AGENT3_SYSTEM, response_schema=_Agent3Output)
    return parsed.model_dump()


def _detect_call(solution_code: str, qualname: str) -> bool:
    """Heurística barata: ¿el último componente del qualname aparece como
    llamada literal en el código? Evita perder tiempo/ejecución en checks
    "call" que ni siquiera están presentes en la solución."""
    func_name = qualname.rsplit(".", 1)[-1]
    return re.search(rf"\b{re.escape(func_name)}\s*\(", solution_code) is not None


class _FakeProblem:
    """Adaptador mínimo para reutilizar executor.grade_submission, que solo
    lee `.rubric` (JSON de checks) del objeto que recibe."""

    def __init__(self, checks: list[dict]):
        self.rubric = json.dumps(checks)


def build_and_validate_rubric(problem: dict, solution_code: str, rubric_proposal: dict) -> tuple[list[dict], str | None]:
    """Construye la rúbrica y la valida EJECUTANDO DE VERDAD la solución de
    referencia con el mismo motor (executor.py) que calificará a los
    estudiantes. El valor "expected" de cada final_value sale de lo que la
    solución realmente produce, nunca de un número que haya dicho el LLM.
    Levanta RuntimeError si la solución no corre limpia o no puntúa 100/100
    contra su propia rúbrica base (final_value).

    Los checks de PROCEDIMIENTO ("function": definir una función matemática
    equivalente a la de la solución; "call": usar una rutina numpy/scipy/
    sklearn concreta) se agregan uno por uno y solo se conservan si no rompen
    la validación 100/100 acumulada — así un ref_body mal escrito, o un
    qualname que no corresponde a nada real, se descarta en silencio en vez
    de tumbar el problema completo. Devuelve (checks, warning): warning no es
    None si ningún check de procedimiento sobrevivió, para que el docente
    sepa que esa rúbrica en particular solo evalúa el resultado final."""
    variables = problem["variables_to_check"]
    fv_points = {vp["name"]: vp["points"] for vp in (rubric_proposal.get("final_value_points") or [])}
    default_points = round(100 / max(len(variables), 1))

    checks = []
    for v in variables:
        name = v["name"]
        points = fv_points.get(name) or v.get("suggested_points") or default_points
        checks.append(
            {
                "id": f"final_{name}",
                "type": "final_value",
                "label": v.get("description") or f"Valor final de {name} correcto",
                "variable": name,
                "expected": 0.0,  # se sobreescribe abajo con el valor real
                "tolerance": 1e-4,
                "points": points,
                "_is_matrix": bool(v.get("is_matrix")),  # se limpia antes de guardar, ver abajo
            }
        )

    run_result = executor.run_student_code(solution_code, checks)
    if run_result["stderr"].strip():
        raise RuntimeError(f"la solución de referencia lanzó un error:\n{run_result['stderr']}")

    results = run_result["checks"]
    for c in checks:
        entry = results.get(c["id"], {})
        if "error" in entry or entry.get("value") is None:
            raise RuntimeError(f"la solución no definió la variable '{c['variable']}': {entry.get('error', 'sin valor')}")
        raw = entry["value"]
        if c.pop("_is_matrix"):
            # Vector/matriz: ya llega como lista (anidada si es 2D) desde el
            # ejecutor (numpy .tolist()); se guarda tal cual y se compara por
            # componente (ver executor.values_close), no se fuerza a float().
            if not isinstance(raw, (list, tuple)):
                raise RuntimeError(f"la variable '{c['variable']}' debía ser un vector/matriz y no lo es: {raw!r}")
            c["expected"] = raw
            c["tolerance"] = 1e-4
        else:
            try:
                value = float(raw)
            except (TypeError, ValueError):
                raise RuntimeError(f"la variable '{c['variable']}' no es numérica: {raw!r}")
            c["expected"] = value
            c["tolerance"] = max(abs(value) * 1e-4, 1e-6)

    base_result = executor.run_student_code(solution_code, checks)
    base_graded = executor.grade_submission(base_result, _FakeProblem(checks))
    base_max = sum(c["points"] for c in checks)
    if base_graded["total_score"] < base_max - 1e-6:
        failed = [r["label"] for r in base_graded["checks_report"] if not r["passed"]]
        raise RuntimeError(f"la rúbrica base (final_value) no valida 100/100 contra la solución: {failed}")

    accepted_process_checks: list[dict] = []

    for i, c in enumerate(rubric_proposal.get("function_checks") or []):
        arg_names = c.get("arg_names") or []
        ref_body = (c.get("ref_body") or "").strip()
        test_points = c.get("test_points") or []
        if not arg_names or not ref_body or not test_points:
            continue
        candidate = checks + accepted_process_checks + [
            {
                "id": f"function_{i}",
                "type": "function",
                "label": c.get("label") or "Definir correctamente la función",
                "arg_names": arg_names,
                "ref_body": ref_body,
                "test_points": test_points,
                "points": c.get("points", 15),
            }
        ]
        result = executor.run_student_code(solution_code, candidate)
        graded = executor.grade_submission(result, _FakeProblem(candidate))
        if graded["total_score"] >= sum(x["points"] for x in candidate) - 1e-6:
            accepted_process_checks.append(candidate[-1])

    for i, c in enumerate(rubric_proposal.get("call_checks") or []):
        qualname = c.get("qualname")
        if not qualname or not _detect_call(solution_code, qualname):
            continue
        candidate = checks + accepted_process_checks + [
            {
                "id": f"call_{i}",
                "type": "call",
                "label": c.get("label") or f"Usar {qualname}",
                "qualnames": [qualname],
                "strict": False,
                "points": c.get("points", 10),
            }
        ]
        result = executor.run_student_code(solution_code, candidate)
        graded = executor.grade_submission(result, _FakeProblem(candidate))
        if graded["total_score"] >= sum(x["points"] for x in candidate) - 1e-6:
            accepted_process_checks.append(candidate[-1])

    plot_warning = None
    if problem.get("requires_plot"):
        candidate = checks + accepted_process_checks + [
            {"id": "plot", "type": "plot", "label": "Generar la gráfica pedida", "min_figures": 1, "points": 10}
        ]
        result = executor.run_student_code(solution_code, candidate)
        graded = executor.grade_submission(result, _FakeProblem(candidate))
        if graded["total_score"] >= sum(x["points"] for x in candidate) - 1e-6:
            accepted_process_checks.append(candidate[-1])
        else:
            # El enunciado pedía graficar pero la solución de referencia no
            # dejó ninguna figura abierta: probable descuido del agente 2, no
            # algo que deba tumbar el problema (el resto de la rúbrica ya
            # validó 100/100), pero el docente debe saberlo al revisar.
            plot_warning = (
                "el enunciado pide graficar (requires_plot) pero la solución de referencia no generó "
                "ninguna figura de matplotlib; no se agregó el chequeo de gráfica"
            )

    # blocked_qualnames: se agregan TODOS juntos en un solo check (sin puntos
    # propios) y se validan de una vez — si alguno rompe la solución de
    # referencia (o sea, ella misma necesitaba esa rutina, y el agente 3 se
    # equivocó al proponer bloquearla), se descarta el bloqueo COMPLETO en
    # vez de intentar aislar cuál sobraba: es más seguro no bloquear nada que
    # bloquear la rutina que la propia referencia necesita.
    blocked = [q for q in (rubric_proposal.get("blocked_qualnames") or []) if q]
    if blocked:
        candidate = checks + accepted_process_checks + [
            {"type": "blocked_call", "qualnames": blocked, "points": 0}
        ]
        result = executor.run_student_code(solution_code, candidate)
        graded = executor.grade_submission(result, _FakeProblem(candidate))
        expected_total = sum(x["points"] for x in checks + accepted_process_checks)
        if graded["total_score"] >= expected_total - 1e-6:
            accepted_process_checks.append(candidate[-1])

    process_warning = None
    if not accepted_process_checks:
        process_warning = (
            "no se pudo validar ningún chequeo de procedimiento (función/llamada/gráfica) para este "
            "problema; la rúbrica quedó evaluando solo el resultado final, no el método usado para llegar a él"
        )
    if plot_warning:
        process_warning = f"{process_warning}\n{plot_warning}" if process_warning else plot_warning

    final_checks = checks + accepted_process_checks
    _normalize_points(final_checks)
    return final_checks, process_warning


def _normalize_points(checks: list[dict], target_total: float = 100.0) -> None:
    """Reescala los puntos de la rúbrica final (en el sitio) para que sumen
    EXACTO target_total, preservando el peso relativo entre checks. Sin esto,
    la suma real depende de cuántos checks de procedimiento sobrevivieron la
    validación (algunos se descartan en silencio, ver build_and_validate_rubric)
    y del reparto que haya propuesto el agente 3, que no siempre suma 100 —
    causa típica de que el puntaje calificado no coincidiera con el "100
    puntos" anunciado en el enunciado.

    "blocked_call" queda SIEMPRE en 0 (no es un criterio puntuado, ver
    grade_submission) y nunca recibe el ajuste de redondeo por arrastre: si
    quedara de último en la lista y se le sumara el arrastre, tendría puntos
    que max_score contaría pero que nunca se pueden ganar de verdad."""
    scoreable = [c for c in checks if c["type"] != "blocked_call"]
    total = sum(c["points"] for c in scoreable)
    if total <= 0:
        return
    scale = target_total / total
    for c in scoreable:
        c["points"] = round(c["points"] * scale, 1)
    drift = round(target_total - sum(c["points"] for c in scoreable), 1)
    if drift:
        scoreable[-1]["points"] = round(scoreable[-1]["points"] + drift, 1)


def check_reference_answer(problem: dict, rubric: list[dict]) -> str | None:
    """Chequeo numérico barato (sin llamada a Gemini): compara el valor que
    REALMENTE calculó la solución (ya grabado como "expected" en la rúbrica
    validada) contra la respuesta de referencia que el agente 1 haya
    extraído del .tex original, si la hay. Es solo una señal de alerta para
    el docente -no bloquea la creación del problema-, porque un método
    numérico distinto puede dar un valor distinto y aun así ser válido."""
    ref_value = problem.get("reference_answer")
    ref_var = problem.get("reference_variable")
    if ref_value is None or not ref_var:
        return None
    match = next((c for c in rubric if c.get("variable") == ref_var), None)
    if match is None:
        return f"el .tex original reportaba {ref_var}={ref_value}, pero esa variable no quedó en la rúbrica final"
    computed = match["expected"]
    tol = max(abs(ref_value) * 0.1, 1e-3)  # 10% relativo: métodos numéricos distintos pueden diferir un poco
    if abs(computed - ref_value) > tol:
        return (
            f"el valor calculado de '{ref_var}' ({computed:.6g}) difiere más de un 10% de la respuesta "
            f"de referencia del .tex original ({ref_value:.6g}) — puede ser un método numérico distinto "
            f"igual de válido, o un error de interpretación; revisar antes de publicar"
        )
    return None


_GRADING_SECTION_RE = re.compile(r"###\s*Calificaci[oó]n.*", re.DOTALL | re.IGNORECASE)


def _replace_grading_section(statement_md: str, rubric: list[dict]) -> str:
    """Reemplaza (o agrega si no existía) la sección "### Calificación" del
    enunciado por el desglose REAL de la rúbrica ya validada y normalizada a
    100 puntos (ver _normalize_points), en vez de dejar el texto que escribió
    el agente 1 — que arma esa lista sin saber todavía cuál rúbrica va a
    sobrevivir la validación (algunos checks de procedimiento se descartan en
    silencio si no validan, ver build_and_validate_rubric) ni si el agente 3
    va a repartir los puntos de forma que sumen 100. Esta es la causa típica
    de que el puntaje mostrado al estudiante no coincidiera con el que en
    realidad se calificaba; generar la sección desde la rúbrica final la
    elimina de raíz en vez de depender de que un LLM "cuadre bien las cuentas".
    """
    lines = ["### Calificación (100 puntos)"]
    for c in rubric:
        if c["type"] == "blocked_call":
            continue  # sin label ni puntos propios: no es un criterio que mostrarle al estudiante
        lines.append(f"- {c['points']:g} pts — {c['label']}")
    section = "\n".join(lines)

    match = _GRADING_SECTION_RE.search(statement_md)
    base = statement_md[: match.start()] if match else statement_md
    return base.rstrip() + "\n\n" + section + "\n"


# ---------------------------------------------------------------------------
# Agente 4: auditoría cualitativa (fidelidad al .tex original, claridad,
# consistencia) — corre DESPUÉS de que la rúbrica ya validó 100/100, así que
# nunca bloquea la creación del problema: solo deja una nota para que el
# docente la lea durante la revisión del borrador.
# ---------------------------------------------------------------------------

AGENT4_SYSTEM = """Eres un auditor de calidad para problemas de programación de métodos \
numéricos generados automáticamente a partir de un enunciado original en LaTeX. Recibes el \
fragmento original, el enunciado adaptado, el código de la solución de referencia, la rúbrica, \
y (si aplica) una nota de que el valor calculado difiere del valor de referencia del original.

Evalúa:
- ¿El enunciado adaptado es fiel al problema matemático original (mismos datos, misma pregunta), \
o cambió algo importante sin justificación?
- ¿El enunciado es claro, sin ambigüedad, y no revela la respuesta?
- ¿Los nombres de variables mencionados en el enunciado, starter_code y la rúbrica son consistentes \
entre sí?
- ¿El método usado en la solución de referencia es razonable para lo que pide el enunciado?

Responde ÚNICAMENTE con JSON válido:
{
  "severity": "ok o low o high",
  "summary": "resumen de 1-2 frases para el docente",
  "concerns": ["problema concreto 1", "problema concreto 2"]
}
"severity" debe ser "high" solo si hay un problema que probablemente haga el ejercicio incorrecto \
o injusto para el estudiante; "low" para detalles menores; "ok" si no hay nada que objetar \
(concerns puede ir vacío en ese caso)."""


def agent4_audit(problem: dict, solution_code: str, rubric: list[dict], numeric_note: str | None) -> dict:
    prompt = (
        f"Fragmento original del .tex:\n{problem['source_excerpt']}\n\n"
        f"Enunciado adaptado:\n{problem['statement_md']}\n\n"
        f"Solución de referencia:\n{solution_code}\n\n"
        f"Rúbrica: {json.dumps(rubric, ensure_ascii=False)}"
    )
    if numeric_note:
        prompt += f"\n\nNota automática del chequeo numérico: {numeric_note}"
    parsed: _Agent4Output = _call_gemini(prompt, AGENT4_SYSTEM, response_schema=_Agent4Output)
    return parsed.model_dump()


def _format_review_notes(numeric_note: str | None, audit: dict | None, process_warning: str | None = None) -> str | None:
    parts = []
    if process_warning:
        parts.append(f"[Rúbrica] {process_warning}")
    if numeric_note:
        parts.append(f"[Chequeo numérico] {numeric_note}")
    if audit:
        severity = audit.get("severity", "ok")
        if severity != "ok" or audit.get("concerns"):
            label = {"high": "ALERTA ALTA", "low": "aviso menor"}.get(severity, severity)
            parts.append(f"[Auditoría IA - {label}] {audit.get('summary', '')}")
            for c in audit.get("concerns") or []:
                parts.append(f"  - {c}")
    return "\n".join(parts) if parts else None


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------

def orchestrate_load_tex(tex_path: str, bank_id: int, db, max_problems: int | None = None, max_retries: int = 2) -> dict:
    with open(tex_path, encoding="utf-8") as f:
        tex_source = f.read()

    bank = db.query(models.ProblemBank).filter(models.ProblemBank.id == bank_id).first()
    if not bank:
        raise RuntimeError(f"banco {bank_id} no encontrado")

    drafts, skipped = agent1_parse_tex(tex_source, max_problems=max_problems)
    skipped = [{"title": s["title"], "reason": s["reason"]} for s in skipped]
    for s in skipped:
        print(f"[gemini_agents] omitido por el agente 1 ({bank.title}): {s['title']}: {s['reason']}")

    created = []
    for draft in drafts:
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                solution_code = agent2_generate_solution(draft, previous_error=last_error)
                rubric_proposal = agent3_propose_rubric(draft, solution_code)
                rubric, process_warning = build_and_validate_rubric(draft, solution_code, rubric_proposal)
                draft["statement_md"] = _replace_grading_section(draft["statement_md"], rubric)

                numeric_note = check_reference_answer(draft, rubric)
                try:
                    audit = agent4_audit(draft, solution_code, rubric, numeric_note)
                except QuotaExceededError:
                    raise
                except Exception as e:
                    audit = {"severity": "unknown", "summary": f"auditoría no disponible: {e}", "concerns": []}
                review_notes = _format_review_notes(numeric_note, audit, process_warning)

                problem = models.Problem(
                    bank_id=bank.id,
                    title=draft["title"],
                    statement_md=draft["statement_md"],
                    starter_code=draft["starter_code"],
                    solution_code=solution_code,
                    rubric=json.dumps(rubric),
                    status="draft",
                    review_notes=review_notes,
                )
                db.add(problem)
                db.commit()
                db.refresh(problem)
                created.append(
                    {
                        "id": problem.id,
                        "title": problem.title,
                        "max_score": problem.max_score,
                        "review_notes": problem.review_notes,
                    }
                )
                break
            except QuotaExceededError:
                raise
            except Exception as e:
                last_error = str(e)
                if attempt == max_retries:
                    print(f"[gemini_agents] omitido tras fallar validación ({bank.title}): {draft.get('title', '?')}: {last_error}")
                    skipped.append({"title": draft.get("title", "?"), "reason": last_error})

    return {"bank_id": bank.id, "created": created, "skipped": skipped}
