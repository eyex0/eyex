#!/usr/bin/env bash
set -euo pipefail

# πX Enterprise — Health & Readiness Checks
# Usage: ./scripts/health-check.sh [--wait]

WAIT=${1:-false}

check() {
    local name="$1"
    local cmd="$2"
    local expected="$3"
    
    if [ "$WAIT" = "--wait" ]; then
        for i in $(seq 1 30); do
            result=$(eval "$cmd" 2>/dev/null || echo "FAIL")
            if [ "$result" = "$expected" ]; then
                echo "✓ $name"
                return 0
            fi
            sleep 2
        done
        echo "✗ $name (expected: $expected, got: $result)"
        return 1
    else
        result=$(eval "$cmd" 2>/dev/null || echo "FAIL")
        if [ "$result" = "$expected" ]; then
            echo "✓ $name"
            return 0
        else
            echo "✗ $name (expected: $expected, got: $result)"
            return 1
        fi
    fi
}

echo "πX Health Check — $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "════════════════════════════════════════════════════════"

FAILURES=0

# Infrastructure
check "PostgreSQL" "docker exec pix-postgres pg_isready -U pix 2>/dev/null | grep -c accepting" "1" || FAILURES=$((FAILURES+1))
check "Redis" "docker exec pix-redis redis-cli ping 2>/dev/null" "PONG" || FAILURES=$((FAILURES+1))

# API
API_STATUS=$(curl -sf http://localhost:8000/api/v1/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "FAIL")
if [ "$API_STATUS" = "healthy" ] || [ "$API_STATUS" = "ok" ]; then
    echo "✓ API Health"
else
    echo "✗ API Health (status: $API_STATUS)"
    FAILURES=$((FAILURES+1))
fi

# API endpoints
for ep in /api/v1/health /api/v1/agents/types /api/v1/intelligence-profile/templates /api/v1/dashboard/widgets; do
    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000$ep 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ] || [ "$STATUS" = "401" ]; then
        echo "✓ $ep ($STATUS)"
    else
        echo "✗ $ep ($STATUS)"
        FAILURES=$((FAILURES+1))
    fi
done

# Frontend
FE_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "000")
if [ "$FE_STATUS" = "200" ]; then
    echo "✓ Frontend"
else
    echo "✗ Frontend ($FE_STATUS)"
    FAILURES=$((FAILURES+1))
fi

# Container status
echo ""
echo "Containers:"
docker compose -f docker-compose.production.yml ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || echo "  (compose not running)"

echo ""
if [ $FAILURES -eq 0 ]; then
    echo "═══ ALL CHECKS PASSED ═══"
    exit 0
else
    echo "═══ $FAILURES CHECK(S) FAILED ═══"
    exit 1
fi
