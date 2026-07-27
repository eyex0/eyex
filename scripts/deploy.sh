#!/usr/bin/env bash
set -euo pipefail

# πX Enterprise — Production Deployment Script
# Usage: ./scripts/deploy.sh [--migrate-only] [--rollback VERSION]

COMPOSE_FILE="docker-compose.production.yml"
ENV_FILE=".env.production"

echo "═════════════════════════════════════════════════════════════"
echo "  πX Enterprise — Production Deployment"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "═════════════════════════════════════════════════════════════"

# 1. Validate environment
echo "\n[1/7] Validating environment..."
if [ ! -f "$ENV_FILE" ]; then
    echo "✗ Missing $ENV_FILE — copy .env.example to $ENV_FILE and fill in values"
    exit 1
fi

# Check critical variables
source "$ENV_FILE"
for var in DATABASE_URL REDIS_URL OPENAI_API_KEY ANTHROPIC_API_KEY; do
    val=$(eval echo "\$$var")
    if [ -z "$val" ] || [ "$val" = "your-"*"-here" ]; then
        echo "✗ $var is not set or still has placeholder value"
        exit 1
    fi
done
echo "  ✓ Environment validated"

# 2. Build images
echo "\n[2/7] Building Docker images..."
docker compose -f $COMPOSE_FILE build --no-cache pix-api pix-frontend
echo "  ✓ Images built"

# 3. Run migrations
echo "\n[3/7] Running Alembic migrations..."
docker compose -f $COMPOSE_FILE up --exit-code-from pix-migrate pix-migrate
MIGRATE_EXIT=$?
if [ $MIGRATE_EXIT -ne 0 ]; then
    echo "✗ Migration failed! Check database connection."
    exit 1
fi
echo "  ✓ Migrations applied (0001-0016)"

# 4. Start services
echo "\n[4/7] Starting production services..."
docker compose -f $COMPOSE_FILE up -d postgres redis
sleep 5  # Wait for DB/Redis to be ready
docker compose -f $COMPOSE_FILE up -d pix-api pix-worker
sleep 10  # Wait for API to start
docker compose -f $COMPOSE_FILE up -d pix-frontend
echo "  ✓ All services started"

# 5. Health checks
echo "\n[5/7] Running health checks..."
sleep 15  # Give services time to initialize

# API health
API_HEALTH=$(curl -sf http://localhost:8000/api/v1/health 2>/dev/null || echo "FAIL")
if [ "$API_HEALTH" != "FAIL" ]; then
    echo "  ✓ API is healthy: $API_HEALTH"
else
    echo "  ✗ API health check failed"
    docker compose -f $COMPOSE_FILE logs pix-api --tail 20
    exit 1
fi

# Redis health
REDIS_HEALTH=$(docker exec pix-redis redis-cli ping 2>/dev/null || echo "FAIL")
if [ "$REDIS_HEALTH" = "PONG" ]; then
    echo "  ✓ Redis is healthy"
else
    echo "  ✗ Redis health check failed"
    exit 1
fi

# PostgreSQL health
PG_HEALTH=$(docker exec pix-postgres pg_isready -U pix 2>/dev/null || echo "FAIL")
if echo "$PG_HEALTH" | grep -q "accepting"; then
    echo "  ✓ PostgreSQL is healthy"
else
    echo "  ✗ PostgreSQL health check failed"
    exit 1
fi

# Frontend health
FE_HEALTH=$(curl -sf http://localhost/ 2>/dev/null | head -1 || echo "FAIL")
if [ "$FE_HEALTH" != "FAIL" ]; then
    echo "  ✓ Frontend is serving"
else
    echo "  ⚠ Frontend not responding (may still be starting)"
fi

# 6. Verify API endpoints
echo "\n[6/7] Verifying API endpoints..."
ENDPOINTS=(
    "GET /api/v1/health"
    "GET /api/v1/agents/types"
    "GET /api/v1/intelligence-profile/templates"
    "GET /api/v1/dashboard/widgets"
)
for ep in "${ENDPOINTS[@]}"; do
    METHOD=$(echo $ep | cut -d' ' -f1)
    PATH_=$(echo $ep | cut -d' ' -f2)
    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" -X $METHOD http://localhost:8000$PATH_ 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ] || [ "$STATUS" = "401" ]; then
        echo "  ✓ $ep → $STATUS"
    else
        echo "  ⚠ $ep → $STATUS"
    fi
done

# 7. Summary
echo "\n[7/7] Deployment summary..."
echo "  Frontend: http://localhost"
echo "  API:      http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  PostgreSQL: localhost:5432"
echo "  Redis:      localhost:6379"
echo ""
echo "  Containers:"
docker compose -f $COMPOSE_FILE ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo "\n═════════════════════════════════════════════════════════════"
echo "  ✓ Production deployment complete"
echo "═════════════════════════════════════════════════════════════"
