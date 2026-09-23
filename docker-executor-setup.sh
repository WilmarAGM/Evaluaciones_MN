#!/bin/sh
# Prepara el contenedor ejecutor aislado y la red interna que lo conecta con
# la API, y conecta el contenedor de la API a esa red. Idempotente: se puede
# correr de nuevo tras cada despliegue sin duplicar nada.
#
# Uso: ./docker-executor-setup.sh [nombre-contenedor-api]
# (por defecto "evaluaciones-mn", el nombre que usa el resto del proyecto)
#
# Topología resultante:
#   evaluaciones-internal (red docker "--internal": SIN salida a Internet)
#     - evaluaciones-executor  (sin BD, sin .env, sin código de la app)
#     - evaluaciones-mn        (además sigue en su red normal, con el
#                                puerto 8080 publicado hacia el túnel/host)
#
# El contenedor ejecutor NUNCA debe conectarse a ninguna otra red: eso le
# devolvería salida a Internet (ver auditoría de seguridad, 2026-09-22).
set -eu

APP_CONTAINER="${1:-evaluaciones-mn}"
NETWORK="evaluaciones-internal"
EXECUTOR="evaluaciones-executor"

if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
    docker network create --internal "$NETWORK"
    echo "Red $NETWORK creada (--internal, sin salida a Internet)."
else
    echo "Red $NETWORK ya existía."
fi

if docker inspect "$EXECUTOR" >/dev/null 2>&1; then
    docker rm -f "$EXECUTOR" >/dev/null
fi

# Tope de memoria del contenedor: 75% de la RAM total de la máquina, con un
# piso de 1g (por debajo de eso, solo importar numpy+scipy+sympy+matplotlib ya
# falla — medido) y SIN techo fijo: un techo de "3g, de sobra en cualquier
# máquina" resultó falso en la práctica — bajo 65-100 ejecuciones realmente
# simultáneas con sympy, un límite de 3g en una VM de 8 núcleos causó OOM-kills
# reales del contenedor (ver dmesg / RestartCount, 2026-09-23): en una máquina
# con más núcleos para paralelizar, también hace falta más memoria agregada
# para todos esos procesos a la vez, no un tope arbitrario "grande y punto".
TOTAL_MEM_KB=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
EXECUTOR_MEM_MB=$(( TOTAL_MEM_KB * 75 / 100 / 1024 ))
[ "$EXECUTOR_MEM_MB" -lt 1024 ] && EXECUTOR_MEM_MB=1024
echo "Memoria total de la máquina: $((TOTAL_MEM_KB / 1024))MB -> límite del ejecutor: ${EXECUTOR_MEM_MB}MB"

docker run -d --name "$EXECUTOR" \
    --network "$NETWORK" \
    --init \
    --restart unless-stopped \
    --memory "${EXECUTOR_MEM_MB}m" \
    --pids-limit 4096 \
    --read-only \
    --tmpfs /tmp:rw,size=256m \
    evaluaciones-executor:local
echo "Contenedor $EXECUTOR levantado en $NETWORK."

if docker network inspect "$NETWORK" --format '{{range .Containers}}{{.Name}} {{end}}' | grep -qw "$APP_CONTAINER"; then
    echo "$APP_CONTAINER ya estaba conectado a $NETWORK."
else
    docker network connect "$NETWORK" "$APP_CONTAINER"
    echo "$APP_CONTAINER conectado a $NETWORK (ahora puede llegar a http://$EXECUTOR:9000)."
fi

sleep 2
docker exec "$APP_CONTAINER" python -c "
import urllib.request
with urllib.request.urlopen('http://$EXECUTOR:9000/health', timeout=5) as r:
    print('Verificación OK:', r.read().decode())
"
