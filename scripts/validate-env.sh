#!/usr/bin/env bash
set -euo pipefail

# πX Enterprise — Environment Validation
# Validates that all required env vars are set before deployment

echo "πX Environment Validation"
echo "══════════════════════════════════════════════════════════"

ENV_FILE="${1:-.env.production}"
if [ ! -f "$ENV_FILE" ]; then
    echo "✗ $ENV_FILE not found"
    exit 1
fi

source "$ENV_FILE"

FAILURES=0
check_var() {
    local var="$1"
    local required="${2:-true}"
    local val=$(eval echo "\$$var" 2>/dev/null || echo "")
    
    if [ -z "$val" ]; then
        if [ "$required" = "true" ]; then
            echo "  ✗ $var (MISSING — required)"
            FAILURES=$((FAILURES+1))
        else
            echo "  ⚠ $var (not set — optional)"
        fi
    elif echo "$val" | grep -qi "your-.*-here\|change-me\|placeholder"; then
        echo "  ✗ $var (PLACEHOLDER — replace with real value)"
        FAILURES=$((FAILURES+1))
    else
        echo "  ✓ $var"
    fi
}

echo "Database:"
check_var "DATABASE_URL"
echo ""

echo "Redis:"
check_var "REDIS_URL"
echo ""

echo "Supabase:"
check_var "SUPABASE_URL"
check_var "SUPABASE_SERVICE_ROLE_KEY"
echo ""

echo "AI Providers:"
check_var "OPENAI_API_KEY"
check_var "ANTHROPIC_API_KEY"
check_var "GOOGLE_API_KEY"
check_var "DEEPSEEK_API_KEY"
check_var "COHERE_API_KEY" "false"
echo ""

echo "App:"
check_var "APP_SECRET_KEY"
echo ""

if [ $FAILURES -eq 0 ]; then
    echo "═══ ENVIRONMENT VALID ✓ ═══"
    exit 0
else
    echo "═══ $FAILURES ISSUES FOUND — FIX BEFORE DEPLOYING ═══"
    exit 1
fi
