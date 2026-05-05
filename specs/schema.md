# Pilgrimage — DB Schema

> PostgreSQL 17 + PostGIS 3.5. All coordinates use `GEOMETRY(Point, 4326)` (WGS84).

---

## Tables

### users
| Column | Type | Note |
|--------|------|------|
| id | UUID | PK |
| email | VARCHAR | unique |
| password_hash | VARCHAR | |
| nickname | VARCHAR | |
| home_location | GEOMETRY(Point, 4326) | departure point |
| preferred_themes | JSONB | |
| created_at | TIMESTAMPTZ | |

### tourist_spots
| Column | Type | Note |
|--------|------|------|
| id | UUID | PK |
| external_id | VARCHAR | KTO contentId, unique |
| name | VARCHAR | |
| category | VARCHAR | |
| theme_tags | JSONB | |
| location | GEOMETRY(Point, 4326) | **GiST index required** |
| operating_hours | JSONB | |
| entrance_fee | INT | |
| address | VARCHAR | |
| avg_review_score | NUMERIC(3,2) | |
| avg_cost | INT | |
| avg_stay_minutes | INT | |
| synced_at | TIMESTAMPTZ | |

### routes
| Column | Type | Note |
|--------|------|------|
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
| Column | Type | Note |
|--------|------|------|
| id | UUID | PK |
| route_id | UUID | FK → routes |
| spot_id | UUID | FK → tourist_spots |
| sequence_order | SMALLINT | UNIQUE(route_id, sequence_order) |
| segment_distance_km | NUMERIC(6,2) | |
| segment_cost | INT | |
| segment_duration_minutes | INT | |

### visit_logs
| Column | Type | Note |
|--------|------|------|
| id | UUID | PK |
| user_id | UUID | FK → users |
| spot_id | UUID | FK → tourist_spots |
| status | VARCHAR | CHECK: UNVISITED / CERTIFIED / REJECTED |
| stay_start_at | TIMESTAMPTZ | |
| stay_end_at | TIMESTAMPTZ | |
| stay_minutes | INT | |
| certified_at | TIMESTAMPTZ | nullable |

### gps_logs
| Column | Type | Note |
|--------|------|------|
| id | UUID | PK |
| user_id | UUID | FK → users |
| location | GEOMETRY(Point, 4326) | GiST index |
| recorded_at | TIMESTAMPTZ | composite index: (user_id, recorded_at) |

> Auto-deleted 30 days after certification (data minimization)

### reviews
| Column | Type | Note |
|--------|------|------|
| id | UUID | PK |
| visit_log_id | UUID | FK → visit_logs, **UNIQUE** (one review per certified visit) |
| spot_id | UUID | FK → tourist_spots |
| user_id | UUID | FK → users |
| rating | SMALLINT | CHECK 1..5 |
| body | TEXT | |
| entrance_fee | INT | |
| food_cost | INT | |
| other_cost | INT | |
| photo_paths | JSONB | up to 5 photos, stored locally |
| created_at | TIMESTAMPTZ | |

### route_shares
| Column | Type | Note |
|--------|------|------|
| id | UUID | PK |
| route_id | UUID | FK → routes |
| share_token | UUID | unique |
| expires_at | TIMESTAMPTZ | nullable |

---

## Index Summary

| Table | Index |
|-------|-------|
| tourist_spots | `GiST(location)` |
| gps_logs | `GiST(location)`, `(user_id, recorded_at)` |
| route_spots | `UNIQUE(route_id, sequence_order)` |
| reviews | `UNIQUE(visit_log_id)` |
