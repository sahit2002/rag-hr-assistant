#!/usr/bin/env bash
# Run the HR Policy RAG Assistant backend (FastAPI) and frontend (Next.js) together.
# Usage: ./app.sh [start|backend|frontend|setup]   (default: start)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
PYTHON="${PYTHON:-python3}"

setup_backend() {
  [ -f "$BACKEND/.env" ] || { cp "$BACKEND/.env.example" "$BACKEND/.env"; echo "Created backend/.env - set GROQ_API_KEY in it."; }
  if [ ! -d "$BACKEND/.venv" ]; then
    echo "Creating Python virtualenv..."
    "$PYTHON" -m venv "$BACKEND/.venv"
    "$BACKEND/.venv/bin/pip" install --upgrade pip
    "$BACKEND/.venv/bin/pip" install -r "$BACKEND/requirements.txt"
  fi
}

setup_frontend() {
  [ -f "$FRONTEND/.env.local" ] || { cp "$FRONTEND/.env.example" "$FRONTEND/.env.local"; echo "Created frontend/.env.local."; }
  if [ ! -d "$FRONTEND/node_modules" ]; then
    echo "Installing frontend dependencies..."
    (cd "$FRONTEND" && npm install)
  fi
}

run_backend() {
  cd "$BACKEND"
  exec .venv/bin/uvicorn main:app --reload --port "$BACKEND_PORT"
}

run_frontend() {
  cd "$FRONTEND"
  exec npm run dev -- --port "$FRONTEND_PORT"
}

case "${1:-start}" in
  setup)
    setup_backend
    setup_frontend
    ;;
  backend)
    setup_backend
    run_backend
    ;;
  frontend)
    setup_frontend
    run_frontend
    ;;
  start)
    setup_backend
    setup_frontend
    trap 'echo; echo "Stopping..."; kill 0' INT TERM EXIT
    (run_backend) &
    (run_frontend) &
    echo "Backend:  http://localhost:$BACKEND_PORT  (docs: /docs)"
    echo "Frontend: http://localhost:$FRONTEND_PORT"
    echo "Press Ctrl+C to stop both."
    wait
    ;;
  *)
    echo "Usage: $0 [start|backend|frontend|setup]" >&2
    exit 1
    ;;
esac
