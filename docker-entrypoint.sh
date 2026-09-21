#!/bin/sh
set -e

cd /app/backend

# Migraciones idempotentes de esquema, ANTES de los seeds (que ya usan el
# modelo nuevo). Si la BD aún no existe o le faltan tablas, no hacen nada.
python -m app.migrate_attempt_problems /app/data/evaluaciones.db
python -m app.migrate_session_proctoring /app/data/evaluaciones.db

# Idempotente: cada función de seed ya verifica si el dato existe antes de crearlo.
python -m app.seed
# import_students (roster legado LMN.xls) ya NO corre al arrancar: recrearía los
# estudiantes que el admin/docente borró. Los rosters se cargan con el .xlsx del docente.
python -m app.seed_taller
python -m app.seed_parcial2

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
