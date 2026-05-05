# Pilgrimage — CLAUDE.md

> 2026 관광데이터 활용 공모전 ① 웹·앱 개발 부문  
> 맞춤형 관광 경로 플랫폼 (GPS 인증 + KTO OpenAPI)

---

## Behavioral guidelines

- 불명확하면 구현 전에 먼저 물어볼 것. 가정하지 말 것.
- 요청한 것만 구현. 추측성 기능·추상화·에러 처리 추가 금지.
- 건드린 코드만 정리. 관련 없는 코드 개선·삭제 금지.
- 멀티스텝 작업은 시작 전에 간단한 계획을 먼저 제시할 것.

---

## 프로젝트 개요

| 항목 | 값 |
|------|----|
| 목적 | 테마 기반 관광 경로 추천 + GPS 30분 체류 인증 |
| 배포 대상 | Raspberry Pi 5 (ARM64) + Ubuntu 24.04 LTS |
| 인증 | SimpleJWT (Access 1h / Refresh 14d) |
| 좌표계 | SRID 4326 (WGS84) — Kakao Maps와 동일 |

---

## 현재 진행상태

> 마지막 업데이트: 2026-05-05  
> 목표: 프로토타입 우선 — 개발 환경에서 빠르게 동작하는 버전 완성 후 배포 환경으로 전환

> **개발 환경은 Docker 미사용** — PostgreSQL·Redis·Django·Vite 모두 로컬 직접 실행. Docker는 배포(Phase 4)에서만 사용.

### Phase 1 · 개발 환경 설정
| 항목 | 상태 |
|------|------|
| 설계/기획 (기능 명세 F01~F09, DB 스키마, API 명세) | ⬜ 미완료 |
| `.env.example`, `.gitignore`, GitHub Actions | ⬜ 미완료 |
| `pyproject.toml` + `package.json` 초기화 | ⬜ 미완료 |
| 로컬 PostgreSQL(PostGIS) + Redis 설치 및 DB 생성 | ⬜ 미완료 |

### Phase 2 · 코드 구현
> 구현 전 반드시 읽을 것: [`specs/functions.md`](specs/functions.md) (기능 명세 F01~F09) · [`specs/schema.md`](specs/schema.md) (DB 스키마) · [`specs/api.md`](specs/api.md) (엔드포인트 + KTO 연동 전략)

| 항목 | 상태 |
|------|------|
| DB 모델 및 마이그레이션 (GeoDjango, PointField) | ⬜ 미완료 |
| KTO OpenAPI 연동 모듈 (kto_sync, `manage.py sync_spots` 수동 실행) | ⬜ 미완료 |
| 핵심 비즈니스 로직 (경로 탐색, GPS 인증 판정, 스코어링) | ⬜ 미완료 |
| DRF API 레이어 (ViewSet, Serializer, Permission) | ⬜ 미완료 |
| 보안 및 예외 처리 (JWT, CORS, 파일 검증) | ⬜ 미완료 |
| React 19 프론트엔드 (지도, GPS 훅, 페이지) | ⬜ 미완료 |

### Phase 3 · 테스트
| 항목 | 상태 |
|------|------|
| pytest-django (경로 알고리즘, GPS 인증, 스코어링) | ⬜ 미완료 |
| vitest (카카오맵 훅, GPS 훅) | ⬜ 미완료 |

### Phase 4 · 배포 환경 설정
| 항목 | 상태 |
|------|------|
| Celery + django-celery-beat 도입 (KTO API 자동 주기 동기화) | ⬜ 미완료 |
| `docker-compose.prod.yml` 작성 | ⬜ 미완료 |
| Dockerfile (backend, frontend) ARM64 최적화 | ⬜ 미완료 |
| GitHub Actions deploy.yml (ghcr.io → RPi5 SSH) secrets 등록 | ⬜ 미완료 |

---

## 절대 하면 안 되는 것

| # | 금지 행위 | 이유 |
|---|-----------|------|
| 1 | `.env` 파일 커밋 | API 키·시크릿 키 유출 — `.env.example`만 커밋 |
| 2 | `index.html`에 Kakao Maps SDK `<script>` 직접 삽입 | `src/lib/kakaoLoader.ts` 싱글턴 로더만 사용 |
| 3 | PostGIS · Kakao 좌표 순서 혼용 | PostGIS `Point(lng, lat)`, Kakao `LatLng(lat, lng)` — 반드시 구분 |
| 4 | GPS 미인증 사용자에게 후기 작성 허용 | `VisitLog.status == "CERTIFIED"` 일 때만 허용 (serializer 검증) |
| 5 | 환경변수 값 코드 하드코딩 | 모든 키·접속 정보는 `.env` 경유 |
| 6 | `linux/amd64` 이미지로 RPi5 배포 | RPi5는 ARM64 — `docker buildx --platform linux/arm64` 필수 |
| 7 | HTTP 환경에서 GPS 인증 운영 | 브라우저 Geolocation API는 HTTPS(Secure Context) 강제 |
| 8 | KTO API 실시간 직접 호출 (캐시·배치 없이) | 일일 트래픽 한도 초과 위험 — Celery 배치 + Redis 캐시 경유 |
| 9 | `/api/shared/:token` 에 인증 추가 | 공유 링크는 비로그인 접근 허용 (`AllowAny`) |
| 10 | 한국어 변수명·함수명 사용 | Python snake_case, TypeScript camelCase 영문만 허용 |

---

## 기술 스택

### 백엔드 (`backend/`)
| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| Python | 3.13 | 런타임 |
| Django | 5.2 LTS | 웹 프레임워크 |
| GeoDjango + PostGIS | 3.5 | 공간 데이터 (PointField, ST_DWithin) |
| DRF | 3.15 | REST API |
| Celery + django-celery-beat | 5 | KTO API 배치 동기화 |
| httpx + tenacity | 0.28 / 9 | KTO API 비동기 클라이언트 + 재시도 |
| psycopg | 3 | PostgreSQL 드라이버 |
| python-decouple | 3.8 | 환경변수 관리 |
| uv | - | 패키지 매니저 (`pyproject.toml`) |

### 프론트엔드 (`frontend/`)
| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| React | 19 | UI |
| Vite | 6 | 빌드 도구 |
| TypeScript | 5 | 타입 안전성 |
| Zustand | 5 | 전역 상태 (auth, route draft) |
| TanStack Query | v5 | 서버 상태 / 캐싱 |
| Axios | 1.7 | HTTP 클라이언트 |
| react-router-dom | 6 | SPA 라우팅 |
| Kakao Maps JS API v3 | - | 지도 (동적 SDK 로딩) |

---

## 디렉토리 구조

```
Pilgrimage/
├── backend/
│   ├── config/              # Django 설정 (base / dev / prod)
│   │   ├── settings/
│   │   ├── urls.py          # /api/ 루트 라우팅
│   │   └── celery.py
│   ├── common/
│   │   ├── exceptions.py    # {"error": {"code", "message"}} 형식
│   │   ├── health.py        # GET /api/health/
│   │   └── themes.py        # 테마 ↔ contentTypeId 매핑
│   └── apps/
│       ├── users/           # AbstractUser, JWT 인증
│       ├── spots/           # TouristSpot (PointField, GistIndex)
│       ├── routes/          # Route, RouteSpot, RouteShare (포크/공유)
│       ├── visits/          # VisitLog, GpsLog, GPS 인증 서비스
│       ├── reviews/         # Review (GPS 인증 완료 후만 작성 가능)
│       └── kto_sync/        # KTO API 클라이언트 + Celery 태스크
├── frontend/
│   └── src/
│       ├── api/             # client.ts, spots/routes/visits/reviews.ts
│       ├── hooks/           # useKakaoMap, useGpsTracking
│       ├── pages/           # HomePage, ThemeSelectPage, MapPage,
│       │                    # RouteSavePage, VisitPage, ReviewPage,
│       │                    # SharedRoutePage
│       ├── store/           # auth.ts (JWT), route.ts (경로 초안)
│       └── lib/             # kakaoLoader.ts (싱글턴 SDK 로더)
├── nginx/nginx.conf         # /api/ → backend:8000, / → SPA
├── docker-compose.yml       # 개발 (볼륨 마운트 + hot reload)
├── docker-compose.prod.yml  # 프로덕션 (ghcr.io 이미지)
└── .github/workflows/
    ├── ci.yml               # PR/push → ruff + pytest + tsc build
    └── deploy.yml           # main push → ARM64 build → RPi5 SSH deploy
```

---

## 주요 도메인 규칙

### GPS 인증 (`apps/visits/services.py`)
```
반경: 200m (GPS_CERT_RADIUS_M)
최소 체류: 30분 (GPS_CERT_MIN_MINUTES)
이탈 허용: 10분 (GPS_CERT_GRACE_MINUTES)
로그 간격: 30초 (GPS_LOG_INTERVAL_SEC)
위조 탐지: 200km/h 초과 이동 → REJECTED
```
- **HTTPS 필수** — 브라우저 Geolocation API는 비보안 HTTP에서 거부됨
- **탭 활성 제한** — Page Visibility API(`useGpsTracking`)로 비활성 시 flush

### 테마 ↔ contentTypeId (`common/themes.py`)
| 테마 키 | UI 레이블 | contentTypeId | 비고 |
|---------|-----------|---------------|------|
| mixed | 혼합 | 12,14,15,28,38,39 | 전체 조합 |
| nature | 자연 | 12 | |
| heritage | 유적 | 14 | |
| urban | 도시 | 14,38,39 | 문화+쇼핑+맛집 |
| festival | 축제 | 15 | |
| leisure | 레저 | 28 | |
| shopping | 쇼핑 | 38 | |
| food | 맛집 | 39 | |
| camping | 캠핑 | — | 고캠핑 정보 조회서비스 (별도 API) |
| medical | 의료/웰니스 | — | 의료관광정보 + 웰니스관광정보 (별도 API) |
| family | 효도 | 12,14,39 | + 무장애 여행 정보 API |

### API 응답 형식
성공: DRF 기본 형식  
오류: `{"error": {"code": "ERROR_CODE", "message": "사용자 메시지", "detail": {}}}`

---

## 개발 환경 설정

> 개발 환경은 Docker 없이 로컬 직접 실행. 아래 순서대로 진행.

**1. 사전 설치 (macOS)**
```bash
brew install postgresql@17 postgis redis gdal
```
> GeoDjango는 GDAL이 로컬에 반드시 있어야 한다. `gdal-config --version` 으로 확인.

**2. DB 준비**
```bash
createdb pilgrimage
psql pilgrimage -c "CREATE EXTENSION postgis;"
```

**3. 환경변수**
```bash
cp .env.example .env
# .env 에 실제 키 입력: KAKAO_JS_KEY, KTO_API_KEY 등
```

**4. 백엔드**
```bash
cd backend
uv pip install -r pyproject.toml
python manage.py migrate
python manage.py runserver
```

**5. 프론트엔드** (별도 터미널)
```bash
cd frontend
npm install
npm run dev
```

**6. Redis** (별도 터미널)
```bash
redis-server
```

**7. KTO 시드 데이터 동기화** (수동)
```bash
python manage.py sync_spots
```

---

## 자주 쓰는 명령어

```bash
# 백엔드 lint
python3 -m ruff check backend/

# 백엔드 테스트
docker compose exec backend pytest -q

# 프론트엔드 타입 체크
cd frontend && node_modules/.bin/tsc --noEmit

# 프론트엔드 빌드 확인
cd frontend && VITE_KAKAO_JS_KEY=dummy node_modules/.bin/vite build
```

---

## 환경변수 (`.env`)

| 키 | 설명 |
|----|------|
| `SECRET_KEY` | Django 시크릿 키 |
| `POSTGRES_*` | DB 접속 정보 |
| `REDIS_URL` | `redis://redis:6379/0` |
| `KTO_API_KEY` | 한국관광공사 OpenAPI 키 |
| `KAKAO_JS_KEY` | 카카오 JS API 키 (백엔드 참조용) |
| `VITE_KAKAO_JS_KEY` | 카카오 JS API 키 (프론트 빌드 주입) |
| `VITE_API_BASE_URL` | `/api` |
| `RPI5_HOST` | RPi5 IP/도메인 |
| `RPI5_USER` | SSH 사용자명 |

> `.env`는 절대 커밋하지 않는다. `.env.example`만 커밋한다.

---

## 중요한 제약사항

- **Kakao SDK** — `index.html`에 `<script>` 태그 금지. `src/lib/kakaoLoader.ts` 의 싱글턴 동적 로더를 반드시 사용
- **ARM64** — `docker buildx --platform linux/arm64` 로 빌드. `postgis/postgis:17-3.5` 이미지 사용
- **좌표 순서** — PostGIS `Point(lng, lat)`, Kakao Maps `LatLng(lat, lng)` — 혼동 주의
- **후기 작성** — `VisitLog.status == "CERTIFIED"` 일 때만 허용 (serializer 검증)
- **경로 공유** — `/shared/:token` 은 인증 없이 접근 가능 (`AllowAny`)

---