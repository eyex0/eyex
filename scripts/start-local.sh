#!/usr/bin/env bash
# Start a complete local πX development environment.
# Requires Docker, Docker Compose, Python, and npm.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT/pix-backend"
FRONTEND_DIR="$ROOT"
PID_FILE="$ROOT/.local-pids"

wait_postgres() {
    local container="${1:-pix-postgres}"
    echo "==> Waiting for Postgres container '$container' to be ready..."
    for _ in $(seq 1 60); do
        if docker exec "$container" pg_isready -U pix >/dev/null 2>&1; then
            echo "Postgres is ready."
            return
        fi
        sleep 1
    done
    echo "ERROR: Postgres did not become ready within 60 seconds." >&2
    exit 1
}

echo "==> πX local dev start"

if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "ERROR: Backend .env not found. Copy $BACKEND_DIR/.env.example to $BACKEND_DIR/.env and fill in real values." >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is not installed. Install Docker Desktop first: https://www.docker.com/products/docker-desktop" >&2
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: npm is not installed. Install Node.js first." >&2
    exit 1
fi

if ! command -v python >/dev/null 2>&1; then
    echo "ERROR: python is not installed." >&2
    exit 1
fi

echo "==> Starting Postgres and Redis via Docker Compose"
(cd "$ROOT" && docker compose -f docker-compose.yml up -d postgres redis)

wait_postgres

echo "==> Running database migrations"
(cd "$BACKEND_DIR" && python -m alembic upgrade head)

echo "==> Seeding demo data"
(cd "$BACKEND_DIR" && python scripts/seed_demo.py)

echo "==> Starting backend on http://localhost:8000"
(cd "$BACKEND_DIR" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &) || true
BACKEND_PID=$!

echo "==> Starting frontend dev server"
(cd "$FRONTEND_DIR" && npm run dev &) || true
FRONTEND_PID=$!

cat > "$PID_FILE" <<EOF
backend=$BACKEND_PID
frontend=$FRONTEND_PID
EOF

echo "==> Waiting for backend health check"
for _ in $(seq 1 30); do
    if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
        echo "Backend is healthy."
        break
    fi
    sleep 1
done

echo "==> Waiting for frontend dev server"
for _ in $(seq 1 30); do
    if timeout 1 bash -c '</dev/tcp/localhost/3000' 2>/dev/null; then
        echo "Frontend dev server is reachable."
        break
    fi
    sleep 1
done

echo ""
echo "πX local environment is starting."
echo "  Backend:   http://localhost:8000"
echo "  Frontend:  http://localhost:3000"
echo "  Health:    http://localhost:8000/health"
echo ""
echo "To stop:"
echo "  cat $PID_FILE"
echo "  kill <pid>"
echo "  docker compose -f docker-compose.yml down"
