#!/bin/sh
set -e

cd /app/backend

# Si CUALQUIER paso de abajo falla (migración, seed), `set -e` corta el
# script antes de llegar a uvicorn — el contenedor nunca sirve a medio
# arrancar. Pero sin esto, ese fallo queda enterrado entre los logs de
# arranque normales y --restart unless-stopped simplemente reintenta en
# bucle sin que se note por qué. El trap deja un aviso imposible de pasar
# por alto en "docker logs" apenas se sale con error.
trap 'code=$?; if [ "$code" -ne 0 ]; then
    echo "==================================================================="
    echo "ARRANQUE FALLIDO (código $code) — uvicorn NO se inició."
    echo "Revisa el error de arriba. El contenedor se reiniciará solo y volverá"
    echo "a fallar igual hasta que se corrija (--restart unless-stopped)."
    echo "==================================================================="
fi' EXIT

echo "--- Variables de entorno relevantes ---"
[ -n "$EXECUTOR_SERVICE_URL" ] && echo "EXECUTOR_SERVICE_URL=$EXECUTOR_SERVICE_URL" \
    || echo "AVISO: EXECUTOR_SERVICE_URL no está configurada — el código de los estudiantes correrá" \
            "sin aislamiento (modo solo-desarrollo, ver executor.py). No debería pasar en producción."
[ -n "$GEMINI_API_KEY" ] && echo "GEMINI_API_KEY: presente" \
    || echo "AVISO: GEMINI_API_KEY no configurada — la carga de problemas con IA (.tex) fallará al usarse;" \
            "el resto de la plataforma funciona igual."
[ -n "$JWT_SECRET_KEY" ] && echo "JWT_SECRET_KEY: presente" \
    || echo "AVISO: JWT_SECRET_KEY no configurada — se genera una aleatoria al vuelo (ver security.py):" \
            "cada reinicio del contenedor invalida las sesiones de todos los estudiantes."

echo "--- Migraciones de esquema ---"
# Idempotentes, ANTES de los seeds (que ya usan el modelo nuevo). Si la BD
# aún no existe o le faltan tablas, no hacen nada.
python -m app.migrate_attempt_problems /app/data/evaluaciones.db
python -m app.migrate_session_proctoring /app/data/evaluaciones.db
python -m app.migrate_fix_untimed_exams /app/data/evaluaciones.db
python -m app.migrate_global_banks /app/data/evaluaciones.db

echo "--- Datos semilla (idempotentes) ---"
python -m app.seed
# import_students (roster legado LMN.xls) ya NO corre al arrancar: recrearía los
# estudiantes que el admin/docente borró. Los rosters se cargan con el .xlsx del docente.
#
# seed_taller / seed_parcial2 / seed_taller_raices TAMPOCO corren al arrancar
# (encontrado 2026-09-24): cada uno solo verifica "¿ya existe un examen/banco
# con este título?" antes de crear, así que si un docente borraba un examen o
# banco a propósito, el SIGUIENTE reinicio del contenedor (cualquier
# despliegue nuevo) lo recreaba solo, deshaciendo el borrado sin avisar. Para
# cargar ese contenido de fábrica (solo hace falta en una base nueva, o si de
# verdad se quiere restaurar uno de estos exámenes/bancos en particular), se
# corre a mano: docker exec evaluaciones-mn python -m app.seed_taller (etc.)

echo "--- Arrancando uvicorn ---"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
