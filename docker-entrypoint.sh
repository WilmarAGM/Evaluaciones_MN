#!/bin/sh
set -e

cd /app/backend

# Idempotente: cada función de seed ya verifica si el dato existe antes de crearlo.
python -m app.seed
python -m app.import_students
python -m app.seed_taller
python -m app.seed_parcial2

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
