#!/usr/bin/env bash
set -euo pipefail

# ══════════════════════════════════════════════════════════════
# πX Enterprise — Cloudflare Deployment Script
# Deploys frontend to Cloudflare Pages + configures R2, security
# Backend stays on Docker/Container (FastAPI needs persistent runtime)
# ══════════════════════════════════════════════════════════════

echo "═════════════════════════════════════════════════════════════"
echo "  πX Enterprise — Cloudflare Deployment"
echo "═════════════════════════════════════════════════════════════"

# 1. Install Wrangler CLI
echo "\n[1/9] Installing Wrangler CLI..."
npm install -g wrangler@latest

# 2. Authenticate with Cloudflare
echo "\n[2/9] Authenticating with Cloudflare..."
echo "Run: wrangler login"
echo "This will open a browser for OAuth authentication."

# 3. Create R2 bucket for file storage
echo "\n[3/9] Creating R2 bucket: pix-enterprise-storage..."
wrangler r2 bucket create pix-enterprise-storage

# 4. Set environment secrets
echo "\n[4/9] Setting environment secrets..."
echo "Adding secrets to Cloudflare Worker..."

# Supabase
wrangler secret put SUPABASE_URL
wrangler secret put SUPABASE_ANON_KEY
wrangler secret put SUPABASE_SERVICE_ROLE_KEY
wrangler secret put SUPABASE_JWT_SECRET

# AI Providers
wrangler secret put OPENAI_API_KEY
wrangler secret put ANTHROPIC_API_KEY
wrangler secret put GOOGLE_AI_API_KEY
wrangler secret put DEEPSEEK_API_KEY

# Database
wrangler secret put DATABASE_URL

# Redis
wrangler secret put REDIS_URL

# App
wrangler secret put APP_SECRET_KEY

# 5. Build frontend
echo "\n[5/9] Building frontend..."
npm ci
npm run build

# 6. Verify build output
echo "\n[6/9] Verifying build output..."
if [ -d "dist" ]; then
  echo "✓ dist/ directory exists"
  echo "  Size: $(du -sh dist/ | cut -f1)"
  echo "  Files: $(find dist/ -type f | wc -l)"
else
  echo "✗ dist/ directory missing — build failed"
  exit 1
fi

# 7. Deploy to Cloudflare Pages
echo "\n[7/9] Deploying to Cloudflare Workers..."
wrangler deploy

# 8. Configure custom domain
echo "\n[8/9] Custom domain configuration..."
echo "To add a custom domain:"
echo "  1. Go to Cloudflare Dashboard > Workers & Pages > pix-enterprise"
echo "  2. Settings > Custom Domains"
echo "  3. Add: pix.your-domain.com"
echo "  4. Cloudflare will auto-configure DNS + SSL"

# 9. Health check
echo "\n[9/9] Health check..."
DEPLOY_URL=$(wrangler deployments list 2>/dev/null | grep -o 'https://[^ ]*' | head -1)
if [ -n "$DEPLOY_URL" ]; then
  echo "Testing: $DEPLOY_URL"
  curl -sI "$DEPLOY_URL" | head -5
fi

echo "\n═════════════════════════════════════════════════════════════"
echo "  Deployment Complete"
echo "═════════════════════════════════════════════════════════════"
echo "Frontend URL: $DEPLOY_URL"
echo "Backend: Deploy separately via Docker/Container (see below)"
echo ""
echo "Next steps:"
echo "  1. Deploy backend: docker compose up -d pix-api postgres redis"
echo "  2. Point API proxy: Cloudflare Worker route /api/v1/* → backend URL"
echo "  3. Set custom domain in Cloudflare dashboard"
echo "═════════════════════════════════════════════════════════════"
