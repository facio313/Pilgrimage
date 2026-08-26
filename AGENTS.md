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

## Memento MCP

에이전트 간 장기 기억을 공유하는 MCP 서버. 세션이 종료되어도 기억이 유지되며, Claude Code / Cursor / Codex 모두 동일한 서버에 연결된다.

- **서버 위치**: `~/memento-mcp/` (Node.js)
- **엔드포인트**: `http://localhost:57332/mcp`
- **DB**: `memento` (PostgreSQL + pgvector)
- **기동**: `nohup node ~/memento-mcp/server.js > /tmp/memento.log 2>&1 &`

### 에이전트별 연결 설정

| 에이전트 | 설정 파일 |
|----------|----------|
| Claude Code | `~/.claude.json` (user scope, `claude mcp add`로 등록) |
| Cursor | `~/.cursor/mcp.json` |
| Codex | `~/.codex/mcp.json` |

### 기억 유형

| 유형 | 용도 |
|------|------|
| `fact` | 설정값, 버전, 환경 정보 |
| `decision` | 아키텍처 선택과 근거 |
| `error` | 에러 원인과 해결 방법 |
| `preference` | 코딩 스타일, 작업 방식 |
| `procedure` | 배포, 테스트 등 반복 절차 |
| `relation` | 컴포넌트 간 의존성 |
| `episode` | 전후 맥락 포함 서사 기억 |

### ACCESS_KEY

서버 접속에 인증 키가 필요하다. 키는 `~/memento-mcp/.env`의 `MEMENTO_ACCESS_KEY`에 저장되어 있다.
각 에이전트 설정 파일에 `Authorization: Bearer <key>` 헤더로 등록되어 있으므로 별도 설정 불필요.

### 기억 도구 사용 규칙 (모든 에이전트 절대 준수)

세션 골격: **`context 시작 → recall·remember 운용 → reflect 마무리`**

#### 세션 시작
- 세션 시작 시 `context` 도구를 호출하여 기억을 로드한다 (Claude Code는 SessionStart 훅 자동 실행).
- `[기억 시스템]` 또는 `[ANCHOR MEMORY]` 섹션이 있으면 숙지 후 추가 호출 불필요.
- context 후에도 첫 발화의 구체적 키워드에 대해 추가 `recall` 선행 필수.

#### Recall-First (강제 규약)
답변·코드 생성 전 의무 선행 호출. 아래 신호 발생 시 즉시 호출:

| 신호 | 호출 방식 |
|------|----------|
| "이전에", "저번에", 과거 참조 | `recall(text=내용, includeContext=true)` |
| 프로젝트명·서비스명 등장 | `recall(topic=프로젝트명, contextText=작업 요약)` |
| 에러·실패 보고 | `recall(type="error", keywords=[에러 키워드])` |
| 설정·포트·환경변수 언급 | `recall(type="fact", keywords=[설정명])` |
| 빌드·배포·테스트 절차 질문 | `recall(type="procedure", keywords=[프로젝트명])` |
| 아키텍처·기술 결정 회상 | `recall(type="decision", topic=프로젝트명)` |

**침묵 호출 원칙**: recall은 사용자에게 알리지 않고 먼저 수행. 결과 있으면 근거로 답변, 없을 때만 추가 정보 요청.

#### Remember 필수 호출 상황

| 상황 | type | importance |
|------|------|-----------|
| 에러 원인 파악 | error | 0.8 |
| 에러 해결책 확정 | procedure | 0.8 |
| 사용자 선호·스타일 명시 | preference | 0.9 |
| 아키텍처·기술 스택 선택 | decision | 0.7 |
| 서비스 경로·포트·설정값 | fact | 0.6 |
| 배포·빌드 절차 완성 | procedure | 0.7 |
| "기억해", "저장해" 언급 | (지정 타입) | 1.0 |

#### tool_feedback 의무
recall 후 `_meta.searchEventId` 보관 → 답변 직후 `tool_feedback` 호출 (활용 파편 relevant=true, 무관 파편 relevant=false).

#### 세션 종료
중요한 작업 결과는 `reflect`로 저장. 해결된 에러 파편은 `forget`. 미저장 종료 금지.

#### 금지 행위
- recall 없이 추측 답변 / 사용자에게 "이전 설정 알려주세요" 되묻기
- recall 0건에서 즉시 포기 (keywords 재구성·type 제거 등 재시도 의무)
- `_meta.suggestion.recommendedTool` 무시

#### Cursor / Codex용 수동 context 호출 (세션 시작 시)
```bash
curl -s -X POST http://localhost:57332/mcp \
  -H "Authorization: Bearer $(grep MEMENTO_ACCESS_KEY ~/memento-mcp/.env | cut -d= -f2)" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"context","arguments":{}}}'
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
| Auth | Branch contract: `main`/`dev` use bonifacio.work Authelia SSO; every other branch uses local credentials |
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
| GitHub Actions (`deploy.yml` x64 validation gate + ARM64 deploy) | ✅ Done |

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
| `docker-compose.yml` | ✅ Done |
| Dockerfile (backend, frontend) ARM64 optimization | ✅ Done |
| GitHub Actions deploy.yml (x64 test gate → native ARM64 build → GHCR → RPi5 SSH) | ✅ Done (`DEPLOY_KEY` secret 필요) |

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
├── nginx/nginx.conf         # Legacy/local reference for the frontend proxy config
├── frontend/nginx.conf      # Baked into the frontend image: /api/ → backend:8000, / → SPA
├── docker-compose.yml  # Production (ghcr.io images)
└── .github/workflows/
    └── deploy.yml           # main push → x64 validation → ARM64 build → RPi5 SSH deploy
```

### Production deployment

- The `validate` job runs first on x64 Ubuntu with isolated PostGIS 17/PostGIS
  3.5 and Redis 8.2.7 services. It must pass full backend Ruff, migration drift and
  apply checks, pytest, frontend Vitest/build, and Compose configuration
  validation before images can be built or deployed.
- Ruff excludes only generated `**/migrations/*.py` files via `pyproject.toml`;
  all non-migration backend Python source must pass `ruff check .`.
- CI injects `PORTFOLIO_BRANCH` and `PORTFOLIO_AUTH_MODE` explicitly. Validation
  on `main` runs in SSO mode with a non-production direct test secret; it must
  never load or require the production edge-secret file.
- The sequential timeout budget is capped at 80 minutes: 20 minutes for x64
  validation and 60 minutes for the dependent ARM64 build/deploy job, including
  up to 20 minutes waiting for the shared host deployment lock.
- GitHub Actions builds the backend and frontend natively on an ARM64 runner.
- `dev` runs the same validation and ARM64 image builds without a registry
  push. Only `main` pushes immutable commit-SHA images and the convenience
  `latest` tag, then requests the production deployment.
- The server receives only `deploy pilgrimage <commit-sha>` through the restricted CI SSH key.
- Production PostgreSQL is the shared, host-unpublished `cksDB` container. Pilgrimage uses its own `pilgrimage` database and restricted `pilgrimage` login role.
- The backend joins both the application `pilgrimage` network (for Redis) and the external `cksDB` network. Application deploys never create, stop, or remove the database container.
- Production Redis is the digest-pinned `pilgrimageRedis` service on only the application network, with no host port and a dedicated persistent AOF volume. Deploys must require its health and preserve both its container and volume; never reuse another application's Redis.
- The stopped legacy `pilgrimageDB` container and `/home/cks/pilgrimage/dbmnt-rootless` are rollback-only and must not be restarted or deleted until the migration retention period ends.
- The frontend proxy configuration is baked into its image; production does not bind-mount a repository Nginx file.
- Frontend authentication is compiled into the static Vite bundle. The final
  Nginx image retains `PORTFOLIO_BRANCH`/`PORTFOLIO_AUTH_MODE` as environment
  and OCI label provenance only; changing runtime environment cannot change the
  bundle. Rebuild for every mode change, and run `main`/`dev` images only behind
  the trusted SSO edge. Backend and frontend images also contain the mode-0444,
  two-line `/etc/portfolio-auth-build`; Django settings and the Nginx resolver
  entrypoint reject any runtime branch/mode that differs from that build record.
- Production sets `PILGRIMAGE_SSO_ENABLED=true` and builds the frontend with
  `VITE_SSO_ENABLED=true`. Host Nginx must run Authelia `auth_request`, discard
  client identity headers, and overwrite `Remote-User`, `Remote-Email`,
  `Remote-Name`, `Remote-Groups`, and the per-application
  `X-Portfolio-Edge-Secret`. The loopback frontend proxy forwards only those
  trusted headers to Django; direct local login and registration are disabled
  in SSO mode. Every access/refresh token is bound to immutable
  `User.sso_subject == Remote-User`; never link by Django username.
  The v2 `Remote-Groups` contract is a whitespace-free role prefix (`user`,
  `user,admin`, or `user,admin,chief-admin`), the mandatory `portfolio-v2`
  marker, then an ordered subset of `access-react`, `access-vue`,
  `access-dukkeobi`, `access-ddit-finalproject`, `access-monitor`,
  `access-pilgrimage`, `access-multtara`, `access-feelmyrythm`, and
  `access-garak`. A `user` or `admin` needs `access-pilgrimage`; the universal
  chief assignment is exactly `user,admin,chief-admin,portfolio-v2` with no
  explicit grant. During the migration window only the exact v1 assignments
  `user`, `user,developer`, and `user,developer,admin` remain accepted: the
  first two project to role `user` plus Pilgrimage access, while the last
  projects to universal `chief-admin`. `developer` is never a current role or
  token claim. Unknown, duplicate, role-gapped, reordered, whitespace-bearing,
  over-1024-byte, or otherwise noncanonical values fail closed.
  SSO JWTs bind only the immutable subject, effective role,
  `access-pilgrimage`, and contract version; they never snapshot unrelated app
  grants. Every authenticated HTTP, refresh, and logout path revalidates those
  claims against the current edge assertion, so an unrelated grant change does
  not invalidate the session but a role, Pilgrimage entitlement, or contract
  version change does. Local Django staff/superuser/group flags never grant an
  SSO role. Production secrets must use a restricted file mount as documented
  in `docs/sso.md`.
  The backend image runs as UID `10001`, effective GID `0`; rootless production
  mounts a host `cks:cks 0640` file which appears as container `root:root 0640`.
- `/pilgrimage/shared/:token`, its Vite assets, and
  `/api/shared/:token/` remain public. Do not place the SSO gate on those paths.
  `/api/health/` also remains a non-sensitive deployment readiness endpoint
  that requires PostgreSQL and Redis but ignores all authentication headers.
- Deployment must never run a global image/system prune or remove application volumes.
- `cleanup_sso_legacy_auth --canonical-subject <subject>` is dry-run by
  default. Its explicit `--apply` path must lock and project all known domain
  ownership FKs to that subject before deleting an unlinked legacy user, abort
  on any unclassified reverse relation, and remove local passwords,
  permissions, sessions, tokens, and local admin history. Admin `LogEntry` rows
  must be deleted with an exact aggregate count, never relabeled as actions by
  the canonical subject. `--apply` must require reviewed expected
  user/domain-row counts and abort if either changes. Never apply it to
  production without reviewing the aggregate output and taking a database
  snapshot; finish with `--check`. SSO cleanup must never fall back to email or
  username as ownership.

### Branch-bound authentication

- `scripts/portfolio-auth-mode.sh` is the canonical resolver. It reads an
  explicit `PORTFOLIO_BRANCH`, then `GITHUB_REF_NAME`, then the current Git
  branch. `main` and `dev` resolve to `sso`; every other branch resolves to
  `local`.
- An explicit `PORTFOLIO_AUTH_MODE` must equal the resolved mode or startup/build
  fails. `PILGRIMAGE_SSO_ENABLED` and `VITE_SSO_ENABLED` are compatibility
  adapters and must agree with the canonical result.
- Local source checkouts may omit the canonical variables and use Git detection.
  CI, Docker builds, and containers must inject the branch explicitly.
- `npm run dev` and `npm run preview` intentionally assert `local`; they reject
  `main` and `dev` immediately. Start either command only from a non-main/dev
  development branch.
- SSO mode requires the Pilgrimage edge secret during backend startup. Local
  branches require no central SSO and retain registration, password login, JWT
  refresh, and local logout.
- Django admin URLs are registered only in local mode. `/admin/login/` must be
  404 in SSO mode, including direct access to the backend's loopback port.

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
# frontend/.env — local Vite overrides
# frontend/.env.production — committed browser-visible Kakao key and production API base
```

**4. Backend**
```bash
cd backend && uv pip install -r pyproject.toml
python manage.py migrate
python manage.py runserver
```

**5. Frontend** (separate terminal)
```bash
# Run from a non-main/dev development branch; this command is local-auth only.
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
cd frontend && node_modules/.bin/vite build
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
| `VITE_KAKAO_JS_KEY` | frontend/.env.production | Browser-visible Kakao JavaScript key; restrict allowed domains in Kakao Developers |
| `VITE_API_BASE_URL` | frontend | `/api` |
| `PORTFOLIO_BRANCH` | backend/build/Compose | Explicit in CI/images/containers; local checkouts auto-detect Git |
| `PORTFOLIO_AUTH_MODE` | backend/build/Compose | `sso` for `main`/`dev`, otherwise `local`; mismatch is fatal |
| `PILGRIMAGE_SSO_ENABLED` | backend/Compose | `true` only behind the host Authelia `auth_request` boundary |
| `PILGRIMAGE_SSO_EDGE_SECRET_HOST_FILE` | Compose host | Absolute host path to the dedicated `cks:cks` mode-0640 edge-secret file |
| `PILGRIMAGE_SSO_EDGE_SECRET_FILE` | backend/Compose | Preferred in-container path; direct runs accept runtime-owner mode-0400/0600 |
| `PILGRIMAGE_SSO_EDGE_SECRET` | backend/Compose | Development-only >=32-byte printable ASCII fallback |
| `VITE_SSO_ENABLED` | frontend build | Enables startup identity exchange and central logout in the production bundle |
| `RPI5_HOST` | backend | RPi5 IP/domain |
| `RPI5_USER` | backend | SSH username |

> Never commit server-side `.env` files or REST/Admin keys. The committed
> `frontend/.env.production` contains browser-visible Vite variables only.

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
