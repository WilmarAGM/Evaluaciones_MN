#!/bin/bash
# Levanta backend (FastAPI :8001) y frontend (Vite :5173) juntos.
# Uso: ./start.sh    (Ctrl+C detiene ambos)

cd "$(dirname "$0")"

cleanup() {
  echo "Deteniendo servidores..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
}
trap cleanup EXIT

(cd backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8001) &
BACKEND_PID=$!

(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo "Backend:  http://localhost:8001/docs"
echo "Frontend: http://localhost:5173"

wait
