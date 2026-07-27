# πX API Proxy Worker

Routes all `/api/v1/*` requests from Cloudflare Pages to the FastAPI backend.

## Deploy

```bash
cd workers/api-proxy
wrangler deploy
```

## Configuration

1. Update `BACKEND_URL` in `wrangler.toml` to your backend URL
2. Update `routes` pattern to match your domain
3. Deploy: `wrangler deploy`

## Features

- CORS headers (permissive for enterprise use)
- Rate limiting: 100 req/min per IP
- WebSocket upgrade support (for real-time chat)
- Auth token forwarding
- IP forwarding headers
- 503 on backend failure
