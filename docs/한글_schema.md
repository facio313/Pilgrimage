# Pilgrimage — DB 스키마

> PostgreSQL 17 + PostGIS 3.5. 모든 좌표는 `GEOMETRY(Point, 4326)` (WGS84).

---

## 테이블 목록

### users
| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| email | VARCHAR | unique |
| password_hash | VARCHAR | |
| nickname | VARCHAR | |
| home_location | GEOMETRY(Point, 4326) | 출발지 |
| preferred_themes | JSONB | |
| created_at | TIMESTAMPTZ | |

### tourist_spots
| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| external_id | VARCHAR | KTO contentId, unique |
| name | VARCHAR | |
| category | VARCHAR | |
| theme_tags | JSONB | |
| location | GEOMETRY(Point, 4326) | **GiST 인덱스 필수** |
| operating_hours | JSONB | |
| entrance_fee | INT | |
| address | VARCHAR | |
| avg_review_score | NUMERIC(3,2) | |
| avg_cost | INT | |
| avg_stay_minutes | INT | |
| synced_at | TIMESTAMPTZ | |

### routes
| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| creator_id | UUID | FK → users |
| title | VARCHAR | |
| theme_tags | JSONB | |
| transport_mode | VARCHAR | |
| total_distance_km | NUMERIC(8,2) | |
| total_estimated_cost | INT | |
| is_public | BOOLEAN | DEFAULT false |
| fork_from_id | UUID | FK → routes, nullable |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### route_spots
| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| route_id | UUID | FK → routes |
| spot_id | UUID | FK → tourist_spots |
| sequence_order | SMALLINT | UNIQUE(route_id, sequence_order) |
| segment_distance_km | NUMERIC(6,2) | |
| segment_cost | INT | |
| segment_duration_minutes | INT | |

### visit_logs
| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| user_id | UUID | FK → users |
| spot_id | UUID | FK → tourist_spots |
| status | VARCHAR | CHECK: UNVISITED / CERTIFIED / REJECTED |
| stay_start_at | TIMESTAMPTZ | |
| stay_end_at | TIMESTAMPTZ | |
| stay_minutes | INT | |
| certified_at | TIMESTAMPTZ | nullable |

### gps_logs
| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| user_id | UUID | FK → users |
| location | GEOMETRY(Point, 4326) | GiST 인덱스 |
| recorded_at | TIMESTAMPTZ | 복합 인덱스 (user_id, recorded_at) |

> 인증 완료 30일 후 자동 삭제 (개인정보 최소화)

### reviews
| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| visit_log_id | UUID | FK → visit_logs, **UNIQUE** (인증 1건당 후기 1건) |
| spot_id | UUID | FK → tourist_spots |
| user_id | UUID | FK → users |
| rating | SMALLINT | CHECK 1..5 |
| body | TEXT | |
| entrance_fee | INT | |
| food_cost | INT | |
| other_cost | INT | |
| photo_paths | JSONB | 최대 5장, 로컬 저장 |
| created_at | TIMESTAMPTZ | |

### route_shares
| 컬럼 | 타입 | 비고 |
|------|------|------|
| id | UUID | PK |
| route_id | UUID | FK → routes |
| share_token | UUID | unique |
| expires_at | TIMESTAMPTZ | nullable |

---

## 인덱스 요약

| 테이블 | 인덱스 |
|--------|--------|
| tourist_spots | `GiST(location)` |
| gps_logs | `GiST(location)`, `(user_id, recorded_at)` |
| route_spots | `UNIQUE(route_id, sequence_order)` |
| reviews | `UNIQUE(visit_log_id)` |
