/**
 * πX API Proxy Worker — Routes /api/v1/* to the FastAPI backend.
 * Handles: CORS, auth token forwarding, WebSocket upgrade, rate limiting.
 */

const BACKEND_URL = 'https://pix-api.your-domain.com'; // Replace with your backend URL

// Simple in-Worker rate limiting (per-IP, 100 req/min)
const RATE_LIMIT = 100;
const RATE_WINDOW = 60; // seconds
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();

export default {
  async fetch(request: Request, env: unknown, ctx: { waitUntil: (p: Promise<unknown>) => void }): Promise<Response> {
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
          'Access-Control-Allow-Headers': 'Authorization, Content-Type, X-Request-Id',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    // Rate limiting
    const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';
    const now = Date.now();
    const entry = rateLimitMap.get(clientIP);
    if (entry && now < entry.resetAt) {
      if (entry.count >= RATE_LIMIT) {
        return new Response(JSON.stringify({ error: 'Rate limit exceeded' }), {
          status: 429,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      entry.count++;
    } else {
      rateLimitMap.set(clientIP, { count: 1, resetAt: now + RATE_WINDOW * 1000 });
    }

    // WebSocket upgrade
    if (request.headers.get('Upgrade') === 'websocket') {
      const upgradeUrl = BACKEND_URL + url.pathname + url.search;
      const resp = await fetch(upgradeUrl, {
        method: request.method,
        headers: request.headers,
  });
      return resp;
    }

    // Proxy API request
    const proxyUrl = BACKEND_URL + url.pathname + url.search;
    const proxyHeaders = new Headers(request.headers);
    proxyHeaders.set('X-Forwarded-For', clientIP);
    proxyHeaders.set('X-Forwarded-Proto', 'https');
    proxyHeaders.set('X-Real-IP', clientIP);

    try {
      const response = await fetch(proxyUrl, {
        method: request.method,
        headers: proxyHeaders,
        body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : undefined,
      });

      // Clone response to add CORS headers
      const newResponse = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
      });
      newResponse.headers.set('Access-Control-Allow-Origin', '*');
      return newResponse;
    } catch (err) {
      return new Response(JSON.stringify({ error: 'Backend unavailable', detail: String(err) }), {
        status: 503,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      });
    }
  },
};
