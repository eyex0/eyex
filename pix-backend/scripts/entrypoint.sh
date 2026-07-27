#!/bin/bash
set -e

# πX Technologies — Production entrypoint.

APP_ENV="${APP_ENVIRONMENT:-development}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-4}"

echo "Starting πX backend in $APP_ENV mode on $HOST:$PORT"

# Run database migrations before starting the app
echo "Running database migrations..."
alembic upgrade head

# Start Uvicorn with production-friendly defaults
exec uvicorn app.main:app \
  --host "$HOST" \
  --port "$PORT" \
  --workers "$WORKERS" \
  --proxy-headers \
  --forwarded-allow-ips "*" \
  --loop uvloop \
  --http h11 \
  --no-access-log
