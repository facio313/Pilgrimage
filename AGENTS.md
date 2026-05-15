# Pilgrimage — AGENTS.md

> 2026 Korean Tourism Data Competition — Personalized Tourism Route Platform

---

## Behavioral Guidelines

- **Always respond in Korean**, regardless of file or code language.
- Ask before implementing if anything is unclear. Never assume.
- Implement only what was requested. No speculative features or abstractions.
- Only clean up code you touched.
- For multi-step tasks, present a brief plan before starting.

---

## Branch Strategy

| Directory | Branch | AI Tool |
|-----------|--------|---------|
| `Pilgrimage/` | `main` | — (release baseline, no AI tool files) |
| `Pilgrimage/worktrees/dev/` | `dev` | — (integration, shared baseline) |
| `Pilgrimage/worktrees/codex/` | `codex` | OpenAI Codex |
| `Pilgrimage/worktrees/cursor/` | `cursor` | Cursor |
| `Pilgrimage/worktrees/anthropic/` | `anthropic` | Claude Code |

### Flow

```
{tool}/feature-name → {tool} → dev → main
```

- Feature branches: `{tool}/{kebab-case}` — e.g. `codex/gps-verify`
- English kebab-case only.

---

## Project Overview

| Item | Value |
|------|-------|
| Purpose | Theme-based tourism route recommendation + GPS 30-min stay verification |
| Deployment | Raspberry Pi 5 (ARM64) + Ubuntu 24.04 LTS |
| Auth | SimpleJWT (Access 1h / Refresh 14d) |
| Coordinate system | SRID 4326 (WGS84) — same as Kakao Maps |

---

## Domain Rules

### GPS Verification
- Radius: 200m / Min stay: 30min / Grace: 10min / Log interval: 30s
- Speed > 200km/h between logs → REJECTED
- HTTPS required (browser Geolocation API)

### Coordinate Order
- PostGIS: `Point(lng, lat)` — Kakao: `LatLng(lat, lng)` — do NOT confuse

### Review Gate
- Only allowed when `VisitLog.status == "CERTIFIED"`

### Shared Routes
- `GET /api/shared/{token}/` must remain `AllowAny` (no auth)

### KTO API
- Never call in real-time without cache/batch — Celery batch + Redis cache only

---

## Never Do

| Action | Reason |
|--------|--------|
| Commit `.env` | Leaks API keys |
| `<script>` for Kakao SDK in `index.html` | Use `src/lib/kakaoLoader.ts` only |
| Hardcode env vars | All keys through `.env` |
| Deploy `linux/amd64` to RPi5 | ARM64 — use `docker buildx --platform linux/arm64` |
| Korean identifiers in code | `snake_case` / `camelCase`, English only |

---

## Stack

- **Backend**: Python 3.13, Django 5.2, GeoDjango/PostGIS, DRF, httpx, psycopg, uv
- **Frontend**: React 19, Vite 6, TypeScript 5, Zustand, TanStack Query v5, Axios, react-router-dom v6, Kakao Maps JS v3

---

## Specs

- Features F01–F09: `specs/functions.md`
- REST API: `specs/api.md`
- DB schema: `specs/schema.md`
