#!/bin/sh
# Copia consistente de la base de datos (API de backup de SQLite, segura con el
# servidor en marcha), verificada con PRAGMA integrity_check ANTES de guardarse.
#
# Corre cada 15 minutos (evaluaciones-backup.timer). Conserva:
#   frecuentes/  una copia por ejecución, las de las últimas 48 horas
#   diarias/     la primera copia de cada día (UTC), los últimos 30 días
#   evaluaciones_latest.db  la más reciente (mismo nombre de siempre)
#
# Restaurar: parar el contenedor, copiar la copia elegida sobre
# ~/app/docker_data/evaluaciones.db (borrando antes -wal y -shm), arrancar.
#
# Motivo: el 2026-10-06 se perdieron respuestas de un parcial presentado entre
# dos copias de las de cada 6 horas (ver historial del repo).
set -eu
DEST=/var/backups/evaluaciones
FREQ="$DEST/frecuentes"
DAILY="$DEST/diarias"
DB_DIR=/home/wilmar/app/docker_data
TMP="$DB_DIR/.backup_tmp.db"
STAMP=$(date -u +%Y%m%d_%H%M)
DAY=$(date -u +%Y%m%d)
MIN_FREE_KB=1048576   # 1 GB: nunca llenar el disco donde vive la base de datos

mkdir -p "$FREQ" "$DAILY"
chmod 700 "$DEST" "$FREQ" "$DAILY"

FREE_KB=$(df --output=avail -k "$DEST" | tail -1 | tr -d ' ')
if [ "$FREE_KB" -lt "$MIN_FREE_KB" ]; then
    echo "ERROR: solo quedan ${FREE_KB} KB libres; no se hace la copia" >&2
    exit 1
fi

rm -f "$TMP"
docker exec -w /app/backend evaluaciones-mn python -c "
import sqlite3, sys
src = sqlite3.connect('/app/data/evaluaciones.db')
dst = sqlite3.connect('/app/data/.backup_tmp.db')
src.backup(dst)
ok = dst.execute('PRAGMA integrity_check').fetchone()[0]
dst.close(); src.close()
sys.exit(0 if ok == 'ok' else 1)
"

OUT="$FREQ/evaluaciones_$STAMP.db"
mv -f "$TMP" "$OUT"
chmod 600 "$OUT"

cp -f "$OUT" "$DEST/.latest_tmp.db"
mv -f "$DEST/.latest_tmp.db" "$DEST/evaluaciones_latest.db"
chmod 600 "$DEST/evaluaciones_latest.db"

if [ ! -e "$DAILY/evaluaciones_$DAY.db" ]; then
    cp "$OUT" "$DAILY/evaluaciones_$DAY.db"
    chmod 600 "$DAILY/evaluaciones_$DAY.db"
fi

find "$FREQ" -name 'evaluaciones_*.db' -mmin +2880 -delete
find "$DAILY" -name 'evaluaciones_*.db' -mtime +30 -delete

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) copia OK $(basename "$OUT") ($(stat -c %s "$OUT") bytes)" > "$DEST/last_backup.txt"
cat "$DEST/last_backup.txt"
