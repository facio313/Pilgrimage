# Pilgrimage — AGENT.md

> Cursor·기타 코딩 에이전트용 프로젝트 가이드. 상세 일정·진행 표는 [`CLAUDE.md`](CLAUDE.md)와 맞춘다.

---

## 이 파일의 역할

- 구현·리팩터·디버깅을 할 때 **먼저 읽을 최소 룰셋**이다.
- `CLAUDE.md`와 **충돌하면 없어야 하며**, 일정/Phase 표가 바뀌면 두 파일을 함께 갱신한다.

---

## 에이전트 워크플로

1. **요구가 모호하면** 코드를 쓰기 전에 사용자에게 질문한다. 추측으로 범위를 넓히지 않는다.
2. **백엔드·도메인 로직을 건드릴 때** 구현 전에 읽는다: [`specs/functions.md`](specs/functions.md) · [`specs/schema.md`](specs/schema.md) · [`specs/api.md`](specs/api.md).
3. **멀티스텝 작업**이면 짧은 계획을 먼저 제시한다.
4. **요청한 것만** 구현한다. 추측 확장·과한 추상화·불필요한 에러 처리를 추가하지 않는다.
5. **건드린 코드만** 정리한다. 무관한 파일은 “개선” 목적으로 수정·삭제하지 않는다.
6. 사용자에게 알리는 설명은 **한국어**로 한다 (저장소 내 파일·코드 언어와 무관).

---

## 기능 우선순위 (specs)

[`specs/functions.md`](specs/functions.md) 기준. 구현·API·스키마는 아래와 대응한다.

| ID | 요약 | 구현 시 참고 |
|----|------|----------------|
| F01 | 테마 선택(11종) → 관광지 목록 | `common/themes.py`, KTO KorService·지역 API |
| F02 | 지도 클릭 → 주변 플로팅 메뉴·경로 누적 | PostGIS `ST_DWithin` **5km**, 최근접 TSP 근사, 혼잡도 반영 |
| F03 | 조건 입력 → 자동 루트 추천 | 가중 스코어·운영시간·예산, 테마별 가중치 dataclass |
| F04 | 30분·200m 체류 GPS 인증 | `UNVISITED` / `CERTIFIED` / `REJECTED`, 탭·HTTPS 제약 |
| F05 | GPS 인증 방문자만 리뷰 | 평점·본문·비용·사진 최대 5장, `visit_log` FK |
| F06 | 루트 저장·공유·포크 | `/shared/:token` 무로그인, `fork_from_id` |
| F07 | 이동수단·비용 재계산 | car/bus/train/walking/bicycle/mixed, 비용 규칙은 스펙 표준식 |
| F08 | 스팟 상세 | 오디오·포토 등 KTO 서브 API |
| F09 | 다국어(장기) | KTO 외국어 API |

---

## API·연동 요약

- 엔드포인트·인증 표: [`specs/api.md`](specs/api.md) (예: `GET /api/shared/{token}/` **AllowAny**, `POST /api/reviews/` CERTIFIED만).
- KTO 베이스 `https://apis.data.go.kr/B551011/`, `ServiceKey` = `KTO_API_KEY`. 프로토타입은 **`sync_spots` 수동**; 실시간 다건 호출 지양, 운영은 배치·캐시.

---

## 스키마 불변 조건

[`specs/schema.md`](specs/schema.md)

- 모든 점 좌표: **`GEOMETRY(Point, 4326)`** (WGS84).
- **`tourist_spots.location`**, **`gps_logs.location`**: GiST 인덱스.
- **`route_spots`**: `UNIQUE(route_id, sequence_order)`.
- **`reviews.visit_log_id`**: UNIQUE — 인증 방문당 리뷰 1건.
- **`gps_logs`**: 인증 후 **30일 경과 시 자동 삭제** (데이터 최소화).

---

## 프로젝트 요약

| 항목 | 내용 |
|------|------|
| 목적 | 테마별 관광 루트 추천 + GPS 30분 체류 인증 |
| 배포 목표 | Raspberry Pi 5 (ARM64), Ubuntu 24.04 LTS |
| 인증 | SimpleJWT (Access 1h / Refresh 14d) |
| 좌표계 | SRID 4326 (WGS84) — 카카오맵과 동일 |

개발 단계에서는 **Docker 없음** — PostgreSQL, Redis, Django, Vite 로컬 실행. Docker는 Phase 4(운영)·`docker-compose.prod.yml` 등에 한함.

---

## 절대 하지 말 것 (Never Do)

| # | 하지 말 것 | 이유 |
|---|------------|------|
| 1 | `.env` 커밋 | 키 유출 — 커밋 대상은 `.env.example`만 |
| 2 | `index.html`에 카카오맵 `<script>` 삽입 | `frontend/src/lib/kakaoLoader.ts` 단일 로더만 사용 |
| 3 | PostGIS / 카카오 좌표 순서 혼동 | PostGIS: `Point(lng, lat)`, 카카오: `LatLng(lat, lng)` |
| 4 | GPS 미인증 방문에 리뷰 허용 | `VisitLog.status == "CERTIFIED"`일 때만 (시리얼라이저 검증) |
| 5 | 환경 변수 값을 코드에 하드코딩 | 모든 키/자격증명은 `.env` 경유 |
| 6 | RPi5에 `linux/amd64` 이미지 배포 | ARM64 — `docker buildx --platform linux/arm64` |
| 7 | HTTP에서만 GPS 검증에 의존 | Geolocation은 보안 컨텍스트(HTTPS) 필요 |
| 8 | 캐시/배치 없이 실시간 KTO API 호출 | 일 한도 초과 위험 — Celery 배치 + Redis 캐시 |
| 9 | `/api/shared/:token`에 인증 추가 | 공유 루트는 공개 (`AllowAny`) |
| 10 | 코드에 한국어 식별자 사용 | Python `snake_case`, TypeScript `camelCase`, 영문만 |

---

## 도메인 · GPS · API

### GPS 검증 (`apps/visits/services.py` 기준)

```
반경:         200m  (GPS_CERT_RADIUS_M)
최소 체류:    30분 (GPS_CERT_MIN_MINUTES)
유예:         10분 (GPS_CERT_GRACE_MINUTES)
로그 간격:    30초 (GPS_LOG_INTERVAL_SEC)
스푸핑:       연속 로그 간 속도 > 200km/h → REJECTED
```

- 브라우저 Geolocation은 **HTTPS**(또는 localhost 등 보안 컨텍스트) 필요.
- 탭 비활성 시 Page Visibility 기준으로 `useGpsTracking` 등에서 플러시 정책을 따른다.

### 테마 ↔ `contentTypeId`

`backend/common/themes.py` 기준. F01: **11개 테마 키** (mixed … family). camping·medical·family 등은 **별도 KTO API** 조합 가능 (`specs/functions.md`). 지역 선택 시 **지역 우선** 정책.

### API 오류 형식

성공: DRF 기본 형식  
오류: `{"error": {"code": "ERROR_CODE", "message": "...", "detail": {}}}`

---

## 스택 요약

- **백엔드**: Python 3.13, Django 5.2, GeoDjango/PostGIS, DRF, (Phase 4) Celery·beat, httpx·tenacity, psycopg, uv
- **프론트엔드**: React 19, Vite 6, TypeScript 5, Zustand, TanStack Query v5, Axios, react-router-dom v6, Kakao Maps JS v3 (`kakaoLoader` 경유)

디렉터리 구조·환경 변수 표·로컬 실행 순서·자주 쓰는 명령은 [`CLAUDE.md`](CLAUDE.md)의 해당 절을 기준으로 유지한다.

---

## 크리티컬 불변 조건 (변경 시 이중 확인)

- **카카오 SDK**: `index.html` 스크립트 금지 — `frontend/src/lib/kakaoLoader.ts`만
- **ARM64**: 프로덕션 이미지는 `linux/arm64`, PostGIS 이미지 예: `postgis/postgis:17-3.5`
- **좌표 순서**: PostGIS `lng,lat` ↔ 카카오 `lat,lng` — 역주의 금지
- **리뷰 게이트**: CERTIFIED 방문만
- **공유 루트**: 공개 엔드포인트 유지

---

## 브랜치 전략

### 워크트리 구성

| 폴더 | 브랜치 | AI 툴 |
|------|--------|-------|
| `Pilgrimage/` (메인) | `main` | — (릴리즈 기준) |
| `Pilgrimage-codex/` | `codex` | OpenAI Codex |
| `Pilgrimage-cursor/` | `cursor` | Cursor |
| `Pilgrimage-anthropic/` | `anthropic` | Claude Code |

### 브랜치 흐름

```
codex/feature-name ──┐
cursor/feature-name ─┤→ {tool} → dev → main
anthropic/feat-name ─┘
```

1. **기능 브랜치 생성** — 각 툴 브랜치에서 분기
   ```bash
   git checkout -b codex/spot-filter codex
   ```
2. **기능 완료 후** — 해당 툴 브랜치에 머지
   ```bash
   git checkout codex && git merge codex/spot-filter
   ```
3. **검증 완료 후** — `dev`로 머지 (다른 툴 브랜치도 동일)
   ```bash
   git checkout dev && git merge codex
   ```
4. **이상 없으면** — `main`으로 머지
   ```bash
   git checkout main && git merge dev
   ```

### 브랜치 네이밍 규칙

- 툴 기준 브랜치: `codex`, `cursor`, `anthropic`
- 기능 브랜치: `{tool}/{kebab-case-feature}` (예: `codex/gps-verify`, `cursor/route-save`)
- 영문 kebab-case만 사용. 한국어 브랜치명 금지.

---

## 상세 레퍼런스

| 내용 | 문서 |
|------|------|
| Phase별 체크리스트, 전체 디렉터리 트리, 개발 명령, env 표 | [`CLAUDE.md`](CLAUDE.md) |
| 기능 F01–F09 | [`specs/functions.md`](specs/functions.md) |
| REST·KTO 호출 전략 | [`specs/api.md`](specs/api.md) |
| 테이블·인덱스 | [`specs/schema.md`](specs/schema.md) |
| Cursor 에이전트 규칙 (자동 적용) | `.cursor/rules/*.mdc` |
| 인덱싱 제외 (로컬·민감 파일) | [`.cursorignore`](.cursorignore) |
