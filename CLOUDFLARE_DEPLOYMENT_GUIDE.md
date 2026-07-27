# πX Enterprise — Cloudflare Deployment Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  Cloudflare                       │
│                                                  │
│  ┌──────────────┐    ┌─────────────────────────┐ │
│  │  Pages       │    │  R2 Storage              │ │
│  │  (Frontend)  │    │  - File uploads          │ │
│  │  React/Vite  │    │  - Documents              │ │
│  │              │    │  - Datasets               │ │
│  └──────┬───────┘    │  - Embedding backups     │ │
│         │            └─────────────────────────┘ │
│  ┌──────▼───────┐                               │
│  │  Worker      │                               │
│  │  (API Proxy) │                               │
│  │  /api/v1/*   │                               │
│  └──────┬───────┘                               │
│         │                                        │
│  ┌──────▼───────┐    ┌─────────────────────────┐ │
│  │  WAF + SSL   │    │  Rate Limiting           │ │
│  │  DDoS        │    │  100 req/min per IP      │ │
│  └──────────────┘    └─────────────────────────┘ │
└─────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────┐
│              External Services                    │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐│
│  │ Backend  │  │ Supabase │  │  AI Providers    ││
│  │ FastAPI  │  │ Postgres │  │  OpenAI          ││
│  │ Docker   │  │ Auth     │  │  Anthropic       ││
│  │          │  │ Storage  │  │  Google AI      ││
│  │  Redis   │  │          │  │  DeepSeek        ││
│  └──────────┘  └──────────┘  └──────────────────┘│
└─────────────────────────────────────────────────┘
```

## Prerequisites

1. Cloudflare account (free tier works for Pages)
2. Wrangler CLI: `npm install -g wrangler@latest`
3. GitHub repo connected: `https://github.com/eyex0/eyex`
4. Supabase project active
5. Backend deployed (Docker, Railway, Fly.io, or VPS)

## Step 1: Create Cloudflare Pages Project

### Option A: Dashboard (Recommended for first deploy)

1. Go to: https://dash.cloudflare.com → Workers & Pages → Create
2. Connect GitHub repo: `eyex0/eyex`
3. Configure:
   - **Framework preset:** Vite
   - **Build command:** `npm run build`
   - **Build output directory:** `dist`
   - **Root directory:** `/` (repo root)
4. Click "Save and Deploy"

### Option B: Wrangler CLI

```bash
# Authenticate
wrangler login

# Create R2 bucket
wrangler r2 bucket create pix-enterprise-storage

# Deploy
npm run build
wrangler deploy
```

## Step 2: Environment Variables

Set these in Cloudflare Dashboard → Workers & Pages → pix-enterprise → Settings → Variables:

### Frontend (Public — visible in build)
```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_PYTHON_BACKEND_URL=/api/v1
```

### Secrets (Encrypted — not visible)
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
DATABASE_URL=postgresql://user:pass@host:5432/pix_enterprise
REDIS_URL=redis://host:6379
APP_SECRET_KEY=your-64-char-secret
```

### AI Providers (Secrets)
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_AI_API_KEY=AIza...
DEEPSEEK_API_KEY=...
```

### Set via CLI:
```bash
wrangler secret put SUPABASE_URL
wrangler secret put SUPABASE_SERVICE_ROLE_KEY
wrangler secret put SUPABASE_JWT_SECRET
wrangler secret put DATABASE_URL
wrangler secret put REDIS_URL
wrangler secret put APP_SECRET_KEY
wrangler secret put OPENAI_API_KEY
wrangler secret put ANTHROPIC_API_KEY
wrangler secret put GOOGLE_AI_API_KEY
wrangler secret put DEEPSEEK_API_KEY
```

## Step 3: R2 Storage Setup

1. Create bucket: `wrangler r2 bucket create pix-enterprise-storage`
2. Configure CORS on bucket:
```json
[{
  "AllowedOrigins": ["https://pix.your-domain.com"],
  "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
  "AllowedHeaders": ["*"],
  "MaxAgeSeconds": 3600
}]
```
3. The bucket binding `PIX_STORAGE` is configured in `wrangler.jsonc`

## Step 4: Backend Deployment

The FastAPI backend needs persistent runtime — deploy via:

### Docker (Recommended)
```bash
docker compose up -d pix-api postgres redis
```

### Railway / Fly.io / Render
- Connect GitHub repo
- Set root: `pix-backend/`
- Use Dockerfile: `pix-backend/Dockerfile.prod`
- Set all env vars

### Backend URL
Set `BACKEND_URL` in `workers/api-proxy/wrangler.toml` to your backend URL.

## Step 5: API Proxy Worker

The frontend calls `/api/v1/*` which Cloudflare Pages serves via `_redirects`.
The API proxy worker forwards these to the backend.

```bash
cd workers/api-proxy
# Update wrangler.toml: BACKEND_URL = "https://your-backend-url"
wrangler deploy
```

## Step 6: Custom Domain

1. Cloudflare Dashboard → Workers & Pages → pix-enterprise
2. Settings → Custom Domains
3. Add: `pix.your-domain.com`
4. Cloudflare auto-configures DNS + SSL certificate

## Step 7: CI/CD (Automatic)

Cloudflare Pages auto-deploys on every push to `main` branch.
Build command: `npm run build`
Output: `dist/`

## Security Configuration

### WAF (Web Application Firewall)
Enabled by default on Cloudflare. Configure rules:
- Block SQL injection attempts
- Block XSS attempts
- Rate limit: 100 req/min per IP (also in Worker)
- Bot fight mode: On

### SSL
- Cloudflare provides free SSL certificates
- Mode: Full (Strict) recommended
- HSTS: Enabled via `_headers` file
- Minimum TLS: 1.2

### Security Headers
Configured in `public/_headers`:
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- Strict-Transport-Security: max-age=31536000
- Content-Security-Policy: configured
- Referrer-Policy: strict-origin-when-cross-origin

## Verification Checklist

After deployment, verify:

### Frontend
- [ ] Landing page loads at https://pix.your-domain.com
- [ ] Auth pages work (login, register, org setup)
- [ ] Dashboard renders with KPI cards + charts
- [ ] Intelligence Workspace loads (memory, knowledge graph)
- [ ] Agent Command Center shows agents
- [ ] Observatory shows 4 views
- [ ] SPA routing works (direct URL access)

### API
- [ ] `GET /api/v1/health` returns 200
- [ ] `GET /api/v1/status` returns status
- [ ] Auth flow: register → login → JWT token
- [ ] Intelligence Profile: create → get → update
- [ ] Dashboard: generate → list widgets
- [ ] Agents: create → list → execute
- [ ] Knowledge Graph: create → search

### Database
- [ ] Supabase connection: `SELECT 1` succeeds
- [ ] Migrations applied: `alembic upgrade head`
- [ ] Tables exist: `agent_instances`, `memory_chunks`, etc.

### AI Gateway
- [ ] OpenAI: test `POST /api/v1/chat` with model `gpt-4o`
- [ ] Anthropic: test with `claude-3-5-sonnet`
- [ ] Google AI: test with `gemini-1.5-pro`
- [ ] Model router: test strategy switch

### Storage
- [ ] R2 bucket: upload test file
- [ ] File upload: POST to `/api/v1/ingestion`
- [ ] Signed URL: generate and download

### Security
- [ ] SSL: `https://` enforced
- [ ] WAF: test SQL injection blocked
- [ ] Rate limiting: test 100+ rapid requests
- [ ] Security headers: check via `securityheaders.com`
- [ ] CSP: check via browser console

## Performance

Cloudflare Pages provides:
- Global CDN (300+ edge locations)
- Automatic gzip/brotli compression
- HTTP/3 support
- Image optimization
- Edge caching

Expected performance:
- TTFB: <50ms (edge)
- Static assets: cached at edge
- API: proxied to backend (~100-200ms)
- Lighthouse score: 90+ (frontend)

## Files Created

| File | Purpose |
|------|---------|
| `wrangler.jsonc` | Cloudflare Pages + Workers config |
| `public/_headers` | Security headers (CSP, HSTS, etc.) |
| `public/_redirects` | SPA routing + API proxy |
| `workers/api-proxy/` | API proxy worker code |
| `cloudflare-deploy.sh` | Automated deployment script |
| `CLOUDFLARE_DEPLOYMENT_GUIDE.md` | This guide |
