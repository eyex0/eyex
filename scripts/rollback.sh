#!/usr/bin/env bash
set -euo pipefail

# πX Enterprise — Rollback Script
# Usage: ./scripts/rollback.sh [migration_version]
# Example: ./scripts/rollback.sh 0015 (rolls back to 0015)

COMPOSE_FILE="docker-compose.production.yml"
TARGET=${1:-}

echo "═════════════════════════════════════════════════════════════"
echo "  πX Enterprise — Rollback"
echo "═════════════════════════════════════════════════════════════"

if [ -z "$TARGET" ]; then
    echo "Current migration version:"
    docker compose -f $COMPOSE_FILE exec pix-api alembic current 2>/dev/null || echo "  (API not running)"
    echo ""
    echo "Usage: ./scripts/rollback.sh <target_version>"
    echo "  Example: ./scripts/rollback.sh 0015"
    echo "  This rolls back migrations back to (but not including) the target."
    exit 0
fi

echo "Rolling back to migration: $TARGET"

# Stop workers first
echo "\n[1/3] Stopping workers..."
docker compose -f $COMPOSE_FILE stop pix-worker
echo "  ✓ Workers stopped"

# Rollback migration
echo "\n[2/3] Rolling back database..."
docker compose -f $COMPOSE_FILE exec pix-api alembic downgrade $TARGET
echo "  ✓ Database rolled back to $TARGET"

# Restart services
echo "\n[3/3] Restarting services..."
docker compose -f $COMPOSE_FILE start pix-worker
docker compose -f $COMPOSE_FILE restart pix-api
sleep 10
echo "  ✓ Services restarted"

echo "\n═════════════════════════════════════════════════════════════"
echo "  ✓ Rollback complete — now at migration $TARGET"
echo "═════════════════════════════════════════════════════════════"
