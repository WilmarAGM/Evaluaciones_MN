"""Servidor HTTP minimalista (solo librería estándar, sin FastAPI/uvicorn:
menos dependencias = menos superficie de ataque) que corre DENTRO del
contenedor ejecutor aislado. Recibe un script Python ya ensamblado
(construido por app/executor.py en el contenedor de la API, que sí conoce
la rúbrica) y lo ejecuta en un subproceso, igual que antes, pero aquí:

  - Sin red (el contenedor se levanta con --network interno sin salida a
    Internet, o --network none): esta clase no necesita imponer nada extra,
    la ausencia de ruta ya lo bloquea a nivel de contenedor.
  - Sin el código fuente de la aplicación, sin .env, sin la base de datos
    (nada de eso se copia a esta imagen ni se monta en este contenedor).
  - Con límites de CPU y memoria por ejecución (resource.setrlimit), además
    de los límites --memory/--pids-limit del propio `docker run`.

Protocolo: POST /run {"script": str, "timeout": float} -> {"stdout", "stderr"}.
No hay autenticación: el contenedor solo es alcanzable desde la red interna
docker, donde el único par es el contenedor de la API.
"""
import json
import os
import resource
import signal
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Tope de memoria VIRTUAL por ejecución individual (RLIMIT_AS), además del
# --memory (RSS real) del contenedor entero. Solo importar numpy+scipy+
# sympy+matplotlib juntos ya reserva ~1 GB de espacio de direcciones (mmap de
# librerías compartidas de BLAS/LAPACK, no memoria física real usada) —
# medido empíricamente: falla con "failed to map segment" por debajo de eso.
# Este límite es el freno a UN script individual desbocado; no se baja más
# para no romper el uso normal de esas bibliotecas.
MAX_MEMORY_BYTES = 1280 * 1024 * 1024
MAX_CPU_SECONDS = 30
MAX_BODY_BYTES = 2 * 1024 * 1024  # un script de estudiante no debería acercarse a esto


def run_script(script: str, timeout: float) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        # NO se usa preexec_fn: CPython retiene el GIL en TODO el proceso
        # servidor mientras corre código Python arbitrario entre fork() y
        # exec() de un hijo con preexec_fn, así que con muchos hilos
        # arrancando subprocesos a la vez (varios estudiantes pulsando
        # "Ejecutar" casi al mismo tiempo) esos forks se serializan uno por
        # uno en vez de paralelizarse — medido: colapsaba la concurrencia de
        # 30 a 2 peticiones exitosas de 60. `start_new_session=True` logra
        # el mismo aislamiento de grupo de procesos (setsid) sin ese costo
        # -evita fork() lento con código Python en medio-, y los límites de
        # memoria/CPU se aplican DESPUÉS, con prlimit() sobre el hijo ya
        # creado (ver más abajo), no antes.
        proc = subprocess.Popen(
            [sys.executable, "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=tmpdir,
            start_new_session=True,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "MPLBACKEND": "Agg",
                 "MPLCONFIGDIR": "/tmp/matplotlib", "HOME": "/tmp"},
        )
        try:
            # Ventana breve (milisegundos) entre que el proceso existe y
            # queda limitado; el --memory/--pids-limit del contenedor entero
            # sigue aplicando desde el instante cero como respaldo.
            resource.prlimit(proc.pid, resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
            resource.prlimit(proc.pid, resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS))
        except ProcessLookupError:
            pass  # el proceso ya había terminado (script vacío o similar); nada que limitar
        try:
            stdout, stderr = proc.communicate(input=script, timeout=timeout)
            return {"stdout": stdout, "stderr": stderr}
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": f"Tiempo de ejecución excedido ({timeout:g}s)."}
        finally:
            # SIEMPRE se limpia el grupo completo, no solo en el timeout: un
            # script que termina "bien" pero dejó hijos vivos (p.ej. abrió
            # procesos y salió sin esperarlos) tampoco debe dejar sobras.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # ya no quedaba ningún proceso vivo en el grupo
            proc.wait()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # sin logging a stdout/stderr: nada sensible que registrar, y menos ruido

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"ok": True})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/run":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0 or length > MAX_BODY_BYTES:
            self._json(413, {"error": "payload too large or empty"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            script = payload["script"]
            timeout = float(payload.get("timeout", 20))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            self._json(400, {"error": "bad request"})
            return
        result = run_script(script, timeout)
        self._json(200, result)


class Server(ThreadingHTTPServer):
    # El backlog de socket.listen() por defecto en socketserver es 5: con
    # varios estudiantes pulsando "Ejecutar" casi a la vez (un examen real
    # midió picos de 55-100 envíos simultáneos, ver deployment_vercel_
    # cloudflare.md) las conexiones que llegan de más se rechazan con
    # "connection reset" en vez de esperar en cola. request_queue_size sí es
    # ese backlog (nombre heredado de BaseServer, no tiene que ver con
    # threads); daemon_threads=True evita que un hilo colgado bloquee el
    # apagado del proceso.
    request_queue_size = 256
    daemon_threads = True
    allow_reuse_address = True


def main():
    port = int(os.environ.get("PORT", "9000"))
    server = Server(("0.0.0.0", port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
