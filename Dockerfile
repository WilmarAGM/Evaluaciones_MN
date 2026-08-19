# ---- Etapa 1: build del frontend (Vite) ----
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Rutas relativas: el frontend se sirve desde el mismo origen que la API.
ENV VITE_API_BASE=""
RUN npm run build

# ---- Etapa 2: backend (FastAPI) + frontend estático ----
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/app backend/app
COPY Rutinas_MN_Python_Est Rutinas_MN_Python_Est
COPY LMN.xls LMN.xls
COPY --from=frontend-builder /app/frontend/dist frontend_dist
COPY docker-entrypoint.sh docker-entrypoint.sh

RUN chmod +x docker-entrypoint.sh \
    && mkdir -p /app/data \
    && useradd -m appuser \
    && chown -R appuser:appuser /app

ENV DATABASE_URL=sqlite:////app/data/evaluaciones.db
ENV MPLCONFIGDIR=/tmp/matplotlib

USER appuser
EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
