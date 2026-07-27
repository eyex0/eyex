# EyeX Technologies — Changelog

## 2026-07-20

### Developer Experience: Full-Stack CI/CD & Frontend Type Safety

- **Changed:** Added `.github/workflows/ci.yml` with backend tests/lint and frontend lint/build jobs.
- **Changed:** Ran Prettier across the frontend and fixed all `@typescript-eslint/no-explicit-any` errors.
- **Changed:** Replaced implicit `any` types with explicit interfaces in agents, pages, and services.
- **Changed:** Exported `Document` type from `src/services/data/documents.service.ts`.
- **Files modified:** `.github/workflows/ci.yml`, `src/services/data/documents.service.ts`, plus many frontend pages/services/components.
- **Tests:** Backend 390 passed, 0 failed, 0 warnings; frontend build succeeds; frontend lint passes with warnings only.
- **Result:** Every push/PR now runs automated checks for both backend and frontend.

### CI/CD: Database Services & Migrations

- **Changed:** Added PostgreSQL service container to `.github/workflows/ci.yml`.
- **Changed:** Added `alembic upgrade head` step and CI environment variables.
- **Changed:** Updated `alembic/env.py` to read `DATABASE_URL` from the environment when available.
- **Files modified:** `.github/workflows/ci.yml`, `alembic/env.py`
- **Result:** Backend tests now run against a migrated database in CI.

### Security: Org/Workspace-Level Session Ownership

- **Changed:** Added `get_current_org_id` dependency and `org_id_ctx` context variable for org-aware request scoping.
- **Changed:** Scoped `/chat/*`, `/memory/*`, and `/intelligence/*` endpoints to the resolved organization.
- **Changed:** Updated `PersistentMemory` read/write methods to filter and store by `org_id`.
- **Changed:** Updated `AgentOrchestratorService` to propagate `org_id` into the agent graph.
- **Changed:** WebSocket endpoint now resolves the user and sets org context.
- **Files modified:** `app/dependencies.py`, `app/core/context.py`, `app/db/memory.py`, `app/services/agent_service.py`, `app/api/v1/chat.py`, `app/api/v1/memory.py`, `app/api/v1/intelligence.py`, plus tests.
- **Tests:** 390 passed, 0 failed, 0 warnings
- **Result:** Users can no longer access chat or memory sessions belonging to another organization.

### Operations: AI Cost/Runaway Guards

- **Changed:** Added `UserQuotaService` with Redis + in-memory fallback for per-user daily limits.
- **Changed:** Added `chat_daily_message_limit` (default 100) and `intelligence_daily_request_limit` (default 50).
- **Changed:** Enforced quotas on `/chat`, `/chat/stream`, and `/intelligence/analyze`.
- **Changed:** Reduced `ChatRequest.message` max length to 12,000 characters.
- **Files modified:** `app/core/quota.py`, `app/config.py`, `app/dependencies.py`, `app/schemas/chat.py`, `app/api/v1/chat.py`, `app/api/v1/intelligence.py`, plus tests.
- **Tests:** 392 passed, 0 failed, 0 warnings
- **Result:** Users hit a clear 429 daily limit instead of unbounded AI spend.

### Performance: Offload CPU-Bound Pipeline Work to Thread Pool

- **Changed:** `CognitiveDataPipeline` now supports an optional `ThreadPoolExecutor`.
- **Changed:** `canonical_builder.build`, `quality_engine.analyze`, `knowledge_graph.build_graph`, and `confidence_engine.batch_assess` now run in a thread pool to avoid blocking the async event loop.
- **Changed:** Quality and confidence assessments run in parallel via `asyncio.gather`.
- **Files modified:** `app/cognitive_data_layer/pipeline.py`
- **Tests:** 390 passed, 0 failed, 0 warnings
- **Result:** Async endpoints remain responsive during heavy data processing.

### Scalability: Memory Pagination & Limits

- **Changed:** Reduced default conversation limit to 50 and capped at 100.
- **Changed:** Added `offset`/`limit` pagination to `PersistentMemory.get_conversation` and API endpoints.
- **Changed:** Added default `min_importance=0.3` and `limit=200` to `recall_all`.
- **Changed:** Added limits to `recall_by_type` and `get_all_agent_memory`.
- **Files modified:** `app/db/memory.py`, `app/api/v1/chat.py`, `app/api/v1/memory.py`
- **Tests:** 390 passed, 0 failed, 0 warnings
- **Result:** Memory queries are bounded, preventing unbounded data loads as sessions grow.

### Reliability: LangGraph Quality Gate & Timeout Guards

- **Changed:** Fixed quality gate bug where `approved` always defaulted to `True`.
- **Changed:** Materialized quality gate decision (`approved`, `score`) into workflow state for single-source-of-truth routing.
- **Changed:** Added `graph_timeout_seconds` config and `asyncio.wait_for` guard around `graph.ainvoke` to prevent runaway workflows.
- **Files modified:** `app/agents/graph.py`, `app/config.py`
- **Tests:** 390 passed, 0 failed, 0 warnings
- **Result:** Quality gate decisions are accurate; workflows cannot hang indefinitely.

### Security: Endpoint Authentication & Admin Authorization

- **Changed:** Added Supabase JWT validation (`app/core/supabase_auth.py`) and dual-token support in `app/dependencies.py`.
- **Changed:** Added `get_current_user` authentication to `/chat/*`, `/memory/*`, `/intelligence/*`, and WebSocket endpoints.
- **Changed:** Added `is_superuser` role checks to `/admin/*` routes.
- **Changed:** Updated frontend `backend-api.service.ts` to send Supabase access tokens and use `VITE_PYTHON_BACKEND_URL`.
- **Files modified:** `app/dependencies.py`, `app/core/supabase_auth.py`, `app/config.py`, `app/api/v1/chat.py`, `app/api/v1/memory.py`, `app/api/v1/intelligence.py`, `app/api/v1/admin.py`, `src/services/backend-api.service.ts`, plus tests.
- **Tests:** 390 passed, 0 failed, 0 warnings
- **Result:** AI endpoints are no longer publicly accessible; admin routes require superuser role.

### Security: Secret Hygiene

- **Changed:** Replaced real credentials in `.env.example` with placeholder values.
- **Changed:** Added `SECURITY.md` with exposed-credential notice and rotation instructions.
- **Changed:** Verified `.env` and `pix-backend/.env` are not tracked by git.
- **Files modified:** `.env.example`, `SECURITY.md`
- **Tests:** 390 passed, 0 failed, 0 warnings
- **Result:** Future secret commits prevented; rotation instructions documented.

### Release: RC1 — Production Readiness

- **Changed:** Hardened security: production secret validation, encryption key enforcement, security headers middleware, CORS restrictions.
- **Changed:** Fixed all critical runtime bugs: missing imports, SQLAlchemy boolean anti-patterns, async Alembic engine, exception naming, enum types.
- **Changed:** Optimized performance: Redis caching for billing/GTM/health endpoints, agent timeouts, input truncation, request metrics.
- **Changed:** Added observability: structured JSON logging, `/metrics` endpoint, request metrics middleware.
- **Changed:** Added production infrastructure: `Dockerfile.prod`, `docker-compose.prod.yml`, `.env.production.example`, `scripts/backup.sh`, `scripts/entrypoint.sh`.
- **Changed:** Added CI/CD: `.github/workflows/ci.yml` (lint/test/build), `.github/workflows/deploy.yml` (staging/production deploy).
- **Changed:** Eliminated all pytest warnings by fixing agent fallback test mocks.
- **Files modified:** 60+ files across `pix-backend/`
- **Tests:** 390 passed, 0 failed, 0 warnings
- **Result:** EyeX RC1 is ready for production deployment

## 2026-07-19

### Feature: Full MVP Wiring

- **Changed:** Wired all 16 remaining pages to real Supabase data
- **Changed:** CRM, Sales, Finance, HR, Projects, Inventory pages now use useQuery + real data services
- **Changed:** Notifications page wired to Supabase with mark-as-read
- **Changed:** Settings page has real profile management, password change, account deletion
- **Changed:** Documents, DataSources, Reports pages wired to Supabase queries
- **Changed:** AiCopilot wired to chatWithCopilotFn Gemini backend
- **Changed:** API page has full key management (generate, revoke, delete) with localStorage
- **Changed:** Integrations page has static catalog with connect/disconnect toggles
- **Changed:** Marketing page shows CTA to connect data source
- **Files modified:** 15 files (+2113, -759 lines)
- **Tests:** All 24 pages verified HTTP 200
- **Result:** All pages use real data with loading/empty states

### Feature: Complete Product Infrastructure

- **Changed:** Login, Signup, Forgot Password pages with Supabase auth
- **Changed:** AuthProvider with session management
- **Changed:** ProtectedRoute wrapper on all 18 app routes
- **Changed:** Server-side Supabase client for SSR
- **Changed:** Contact page with form (react-hook-form + zod)
- **Changed:** 404 NotFound page
- **Changed:** SEO meta tags on all 25 routes
- **Changed:** Full TypeScript types for 26-table schema
- **Changed:** 8 domain data services (Finance, CRM, Sales, HR, Projects, Inventory, Documents, Notifications)
- **Changed:** SiteHeader Login/Sign Up links, SiteFooter Contact link
- **Files modified:** 52 files (+4601, -654 lines)
- **Tests:** All 24 pages verified HTTP 200
- **Result:** Complete auth flow, real data layer, production-ready infrastructure

### Feature: Accessibility and Type Safety

- **Changed:** Added aria-labels to 17+ icon-only buttons
- **Changed:** Replaced 11 `(r: any)` with proper typeof types
- **Changed:** Fixed catch (err: any) to catch (err: unknown)
- **Changed:** Fixed sitemap URL to production domain
- **Changed:** Removed unused imports from Home.tsx
- **Files modified:** 14 files (+30, -34 lines)
- **Tests:** Build clean, deployed
- **Result:** Improved accessibility and type safety

### Fix: Audit Cleanup

- **Changed:** Added /ai-chat and /api to APP_ROUTES
- **Changed:** Removed duplicate nav/footer from Home.tsx and About.tsx
- **Changed:** Fixed AiCopilot invisible text (text-surface-container-high → text-primary-brand)
- **Changed:** Expanded ICONS map in primitives.tsx (16 new icon mappings)
- **Changed:** Removed 4 dead files (use-auth, use-fade-up, storage.service, auth.service)
- **Files modified:** 14 files (+16, -475 lines)
- **Tests:** Build clean, deployed
- **Result:** Fixed duplicate UI, missing icons, dead code

## 2026-07-18

### Feature: Stitch Integration and SSR

- **Changed:** Generated 7 Stitch screens (Home, About, AiChat, AiCopilot, Api, Dashboard, Analytics)
- **Changed:** Converted Stitch HTML to React TSX with lucide-react icons
- **Changed:** Fixed SSR routing for Cloudflare Workers
- **Changed:** Applied SSR patch to index.mjs
- **Files modified:** 20+ files
- **Tests:** SSR working on Cloudflare
- **Result:** Stitch-generated pages integrated with SSR

### Feature: Pro Design System

- **Changed:** Dark theme (#050505 bg, #38BDF8 primary, Geist fonts)
- **Changed:** Custom CSS utilities (bento-card, glass-nav, luminous-btn, fade-up, ambient-glow)
- **Changed:** MD3 color tokens (surface, on-surface, outline, etc.)
- **Changed:** BrandMark with lucide-react Eye icon
- **Files modified:** 10+ files
- **Tests:** Visual verification
- **Result:** Consistent dark enterprise design

### Feature: Initial Setup

- **Changed:** Merged pix_tech codebase (src/, configs, package.json)
- **Changed:** Custom AI agent framework (8 agents + orchestrator)
- **Changed:** Replaced Material Symbols with lucide-react
- **Changed:** Cloudflare Workers deployment
- **Files modified:** 50+ files
- **Tests:** Build clean, deploy working
- **Result:** Foundation for the complete product
