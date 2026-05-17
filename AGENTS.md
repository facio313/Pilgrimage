# Pilgrimage — AGENTS.md

> 2026 Korean Tourism Data Competition — Web/App Development
> Personalized Tourism Route Platform (GPS Verification + KTO OpenAPI)

---

## ⚠️ Agent Authority Boundaries — MUST READ FIRST

### 1. Branch Scope per Agent

Each AI agent may only work within its own tool branch and below.
**`main` and `dev` branches are managed exclusively by the user.**

| Branch | Who controls it |
|--------|----------------|
| `main` | User only |
| `dev` | User only |
| `anthropic` | Claude Code (this agent) |
| `cursor` | Cursor |
| `codex` | OpenAI Codex |
| `{tool}/feature-*` | Each respective agent |

- Agents **must not** commit, merge, or push to `main` or `dev` without an explicit user request.
- When the user explicitly asks, agents may assist with `main`/`dev` operations.

### 2. Shared Project Information → Always Update `AGENTS.md`

If a change affects project-wide rules, constraints, architecture, or any information that all agents should know:

> **Update `AGENTS.md` — not individual tool config files.**

Individual files (`CLAUDE.md`, `.cursor/rules/`, etc.) are thin wrappers that reference `AGENTS.md`.
Editing only a tool-specific file means the other agents will miss the update.

| Type of change | Where to update |
|----------------|----------------|
| Project rules, domain logic, API spec, constraints | `AGENTS.md` ✅ |
| Claude Code-only settings | `.claude/` |
| Cursor rule formatting / always-apply tweaks | `.cursor/rules/pilgrimage-core.mdc` |
| Codex-only instructions | `AGENTS.md` (Codex reads this directly) |

---

## Vowline

<!-- vowline:start -->
Always use the skill `vowline` consistently, including for all sub-agents.
<!-- vowline:end -->

Vowline은 에이전트가 작업을 증거 기반으로 수행하고, 결과를 공개 인터페이스로 검증하도록 강제하는 cross-cutting 운영 스킬이다.
모든 에이전트에 전역 설치되어 있으며, 실질적인 작업(구현, 수정, 검증)에는 항상 활성화한다.

### 설치 상태

| 에이전트 | 전역 스킬 경로 | 활성화 방식 |
|----------|---------------|------------|
| Claude Code | `~/.claude/skills/vowline/` | `~/.claude/CLAUDE.md` 마커 블록 |
| Codex | `~/.agents/skills/vowline/` | `~/.codex/AGENTS.md` 마커 블록 |
| Cursor | `~/.cursor/skills/vowline/` | `.cursor/rules/vowline.mdc` (alwaysApply) |

### 호출 방법

| 에이전트 | 호출 접두어 | 예시 |
|----------|------------|------|
| Claude Code | `/vowline` | `/vowline fix the GPS verification service and verify it` |
| Codex | `$vowline` | `$vowline build the route algorithm and run tests` |
| Cursor | 자동 적용 (alwaysApply) | 별도 호출 불필요 |

### 업데이트

```bash
git clone https://github.com/chojondocho/vowline.git /tmp/vowline
python3 /tmp/vowline/install.py global --harnesses core
```

---

## Behavioral guidelines

- **Always respond in Korean**, regardless of the language used in files or code.
- Ask before implementing if anything is unclear. Never assume.
- Implement only what was requested. No speculative features, abstractions, or error handling.
- Only clean up code you touched. Do not improve or delete unrelated code.
- For multi-step tasks, present a brief plan before starting.

---

## Project Overview

| Item | Value |
|------|-------|
| Purpose | Theme-based tourism route recommendation + GPS 30-min stay verification |
| Deployment | Raspberry Pi 5 (ARM64) + Ubuntu 24.04 LTS |
| Auth | SimpleJWT (Access 1h / Refresh 14d) |
| Coordinate system | SRID 4326 (WGS84) — same as Kakao Maps |

---

## Current Progress

> Last updated: 2026-05-06
> Goal: Prototype-first — build a working dev version, then migrate to production

> **No Docker in development** — PostgreSQL, Redis, Django, Vite all run locally. Docker only for Phase 4.

### Phase 1 · Development Environment Setup
| Item | Status |
|------|--------|
| Design/planning (feature specs F01–F09, DB schema, API spec) | ✅ Done |
| `.env`, `.gitignore` | ✅ Done |
| `pyproject.toml` + `package.json` init | ✅ Done |
| Local PostgreSQL (PostGIS) + Redis install and DB creation | ✅ Done |
| GitHub Actions (`ci.yml`, `deploy.yml`) | ⬜ Pending |

### Phase 2 · Implementation
> Read before coding: [`specs/functions.md`](specs/functions.md) · [`specs/schema.md`](specs/schema.md) · [`specs/api.md`](specs/api.md)

| Item | Status |
|------|--------|
| DB models and migrations (GeoDjango, PointField) | ⬜ Pending |
| KTO OpenAPI module (kto_sync, manual `manage.py sync_spots`) | ⬜ Pending |
| Core business logic (route planning, GPS verification, scoring) | ⬜ Pending |
| DRF API layer (ViewSet, Serializer, Permission) | ⬜ Pending |
| Security and error handling (JWT, CORS, file validation) | ⬜ Pending |
| React 19 frontend (map, GPS hook, pages) | ⬜ Pending |

### Phase 3 · Testing
| Item | Status |
|------|--------|
| pytest-django (route algorithm, GPS verification, scoring) | ⬜ Pending |
| vitest (Kakao map hook, GPS tracking hook) | ⬜ Pending |

### Phase 4 · Production Environment
| Item | Status |
|------|--------|
| Celery + django-celery-beat (KTO API scheduled sync) | ⬜ Pending |
| `docker-compose.prod.yml` | ⬜ Pending |
| Dockerfile (backend, frontend) ARM64 optimization | ⬜ Pending |
| GitHub Actions deploy.yml (ghcr.io → RPi5 SSH) secrets | ⬜ Pending |

---

## Never Do

| # | Action | Reason |
|---|--------|--------|
| 1 | Commit `.env` | Leaks API keys |
| 2 | Load Kakao Maps SDK via `<script>` in `index.html` | Use singleton loader at `src/lib/kakaoLoader.ts` only |
| 3 | Mix up PostGIS / Kakao coordinate order | PostGIS: `Point(lng, lat)`, Kakao: `LatLng(lat, lng)` |
| 4 | Allow review without GPS verification | Only when `VisitLog.status == "CERTIFIED"` (serializer check) |
| 5 | Hardcode env var values in code | All keys/credentials must go through `.env` |
| 6 | Deploy `linux/amd64` image to RPi5 | RPi5 is ARM64 — use `docker buildx --platform linux/arm64` |
| 7 | Run GPS verification over HTTP | Browser Geolocation API requires HTTPS (Secure Context) |
| 8 | Call KTO API in real-time without cache/batch | Risk of exceeding daily quota — Celery batch + Redis cache |
| 9 | Add auth to `/api/shared/:token` | Shared routes must be public (`AllowAny`) |
| 10 | Use Korean identifiers in code | Python snake_case, TypeScript camelCase, English only |

---

## Tech Stack

### Backend (`backend/`)
| Library | Version | Purpose |
|---------|---------|---------|
| Python | 3.13 | Runtime |
| Django | 5.2 LTS | Web framework |
| GeoDjango + PostGIS | 3.5 | Spatial data (PointField, ST_DWithin) |
| DRF | 3.15 | REST API |
| Celery + django-celery-beat | 5 | KTO API batch sync (Phase 4 only) |
| httpx + tenacity | 0.28 / 9 | KTO API client (sync mode) + retry |
| psycopg | 3 | PostgreSQL driver |
| python-decouple | 3.8 | Environment variable management |
| uv | - | Package manager (`pyproject.toml`) |

### Frontend (`frontend/`)
| Library | Version | Purpose |
|---------|---------|---------|
| React | 19 | UI |
| Vite | 6 | Build tool |
| TypeScript | 5 | Type safety |
| Zustand | 5 | Global state (auth, route draft) |
| TanStack Query | v5 | Server state / caching |
| Axios | 1.7 | HTTP client |
| react-router-dom | 6 | SPA routing |
| Kakao Maps JS API v3 | - | Map (dynamic SDK loading) |

---

## Directory Structure

```
Pilgrimage/
├── backend/
│   ├── .env                 # Django env vars (not committed)
│   ├── config/              # Django settings (base / dev / prod)
│   │   ├── settings/
│   │   ├── urls.py          # /api/ root routing
│   │   └── celery.py
│   ├── common/
│   │   ├── exceptions.py    # {"error": {"code", "message"}} format
│   │   ├── health.py        # GET /api/health/
│   │   └── themes.py        # theme ↔ contentTypeId mapping
│   └── apps/
│       ├── users/           # AbstractUser, JWT auth
│       ├── spots/           # TouristSpot (PointField, GistIndex)
│       ├── routes/          # Route, RouteSpot, RouteShare (fork/share)
│       ├── visits/          # VisitLog, GpsLog, GPS verification service
│       ├── reviews/         # Review (CERTIFIED visits only)
│       └── kto_sync/        # KTO API client + Celery tasks
├── frontend/
│   ├── .env                 # Vite env vars (not committed)
│   └── src/
│       ├── api/             # client.ts, spots/routes/visits/reviews.ts
│       ├── hooks/           # useKakaoMap, useGpsTracking
│       ├── pages/           # HomePage, ThemeSelectPage, MapPage,
│       │                    # RouteSavePage, VisitPage, ReviewPage,
│       │                    # SharedRoutePage
│       ├── store/           # auth.ts (JWT), route.ts (route draft)
│       └── lib/             # kakaoLoader.ts (singleton SDK loader)
├── specs/                   # Feature specs, DB schema, API reference
├── nginx/nginx.conf         # /api/ → backend:8000, / → SPA
├── docker-compose.prod.yml  # Production (ghcr.io images)
└── .github/workflows/
    ├── ci.yml               # PR/push → ruff + pytest + tsc build
    └── deploy.yml           # main push → ARM64 build → RPi5 SSH deploy
```

---

## Domain Rules

### GPS Verification (`apps/visits/services.py`)
```
Radius:       200m  (GPS_CERT_RADIUS_M)
Min stay:     30min (GPS_CERT_MIN_MINUTES)
Grace period: 10min (GPS_CERT_GRACE_MINUTES)
Log interval: 30sec (GPS_LOG_INTERVAL_SEC)
Spoof detect: speed > 200km/h between consecutive logs → REJECTED
```
- **HTTPS required** — browser Geolocation API blocked on non-secure HTTP
- **Tab active only** — Page Visibility API (`useGpsTracking`) flushes on tab hide

### Theme ↔ contentTypeId (`common/themes.py`)
| Key | UI Label | contentTypeId | Note |
|-----|----------|---------------|------|
| mixed | 혼합 | 12,14,15,28,38,39 | All combined |
| nature | 자연 | 12 | |
| heritage | 유적 | 14 | |
| urban | 도시 | 14,38,39 | culture + shopping + food |
| festival | 축제 | 15 | |
| leisure | 레저 | 28 | |
| shopping | 쇼핑 | 38 | |
| food | 맛집 | 39 | |
| camping | 캠핑 | — | Gocamping API (separate) |
| medical | 의료/웰니스 | — | Medical tourism + Wellness API |
| family | 효도 | 12,14,39 | + Barrier-free travel API |

### API Response Format
Success: DRF default format
Error: `{"error": {"code": "ERROR_CODE", "message": "user-facing message", "detail": {}}}`

---

## Development Setup

> No Docker. Run everything locally in order.

**1. Prerequisites (macOS)**
```bash
brew install postgresql@17 postgis redis gdal
```
> GeoDjango requires GDAL locally. Verify: `gdal-config --version`

**2. Database**
```bash
createdb pilgrimage
psql pilgrimage -c "CREATE EXTENSION postgis;"
```

**3. Environment variables**
```bash
# backend/.env — Django vars (SECRET_KEY, DB, REDIS, KTO_API_KEY, KAKAO_JS_KEY)
# frontend/.env — Vite vars (VITE_KAKAO_JS_KEY, VITE_API_BASE_URL)
```

**4. Backend**
```bash
cd backend && uv pip install -r pyproject.toml
python manage.py migrate
python manage.py runserver
```

**5. Frontend** (separate terminal)
```bash
cd frontend && npm install && npm run dev
```

**6. Redis** (separate terminal)
```bash
redis-server
```

**7. KTO data sync** (manual, run from backend/)
```bash
python manage.py sync_spots
```

---

## Common Commands

```bash
# Backend lint
cd backend && python -m ruff check .

# Backend tests
cd backend && pytest -q

# Frontend type check
cd frontend && node_modules/.bin/tsc --noEmit

# Frontend build check
cd frontend && VITE_KAKAO_JS_KEY=dummy node_modules/.bin/vite build
```

---

## Environment Variables

| Key | Location | Description |
|-----|----------|-------------|
| `SECRET_KEY` | backend | Django secret key |
| `POSTGRES_*` | backend | DB connection info |
| `REDIS_URL` | backend | `redis://localhost:6379/0` |
| `KTO_API_KEY` | backend | Korea Tourism Organization OpenAPI key |
| `KAKAO_JS_KEY` | backend | Kakao JS API key (server-side reference) |
| `VITE_KAKAO_JS_KEY` | frontend | Kakao JS API key (build-time injection) |
| `VITE_API_BASE_URL` | frontend | `/api` |
| `RPI5_HOST` | backend | RPi5 IP/domain |
| `RPI5_USER` | backend | SSH username |

> Never commit `.env`.

---

## Branch Strategy

### Worktree Layout

| Directory | Branch | AI Tool |
|-----------|--------|---------|
| `Pilgrimage/` (main repo) | `main` | — (release baseline) |
| `Pilgrimage/worktrees/codex/` | `codex` | OpenAI Codex |
| `Pilgrimage/worktrees/cursor/` | `cursor` | Cursor |
| `Pilgrimage/worktrees/anthropic/` | `anthropic` | Claude Code |

### Flow

```
codex/feature-name ──┐
cursor/feature-name ─┤→ {tool} → dev → main
anthropic/feat-name ─┘
```

1. Branch off the tool branch for any new feature:
   ```bash
   git checkout -b codex/spot-filter codex
   ```
2. Merge completed feature back into the tool branch:
   ```bash
   git checkout codex && git merge codex/spot-filter
   ```
3. Merge tool branch into `dev` after validation:
   ```bash
   git checkout dev && git merge codex
   ```
4. Merge `dev` into `main` after full verification only.

### Naming Rules

- Tool branches: `codex`, `cursor`, `anthropic`
- Feature branches: `{tool}/{kebab-case-feature}` — e.g. `codex/gps-verify`
- English kebab-case only.

---

## Critical Constraints

- **Kakao SDK** — No `<script>` in `index.html`. Always use `src/lib/kakaoLoader.ts` singleton loader
- **ARM64** — Build with `docker buildx --platform linux/arm64`. Use `postgis/postgis:17-3.5` image
- **Coordinate order** — PostGIS `Point(lng, lat)`, Kakao Maps `LatLng(lat, lng)` — do not confuse
- **Review gate** — Only allowed when `VisitLog.status == "CERTIFIED"` (serializer validation)
- **Shared routes** — `/shared/:token` must remain public (`AllowAny`)

---
