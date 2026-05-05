# Pilgrimage — API Reference

---

## REST Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/auth/register` | Sign up | No |
| POST | `/api/auth/login` | Login (issues JWT) | No |
| POST | `/api/auth/refresh` | Refresh access token | No |
| GET | `/api/spots/?theme=&lat=&lng=&radius=` | Spot list (radius query) | No |
| GET | `/api/spots/{id}/` | Spot detail | No |
| POST | `/api/routes/` | Save route | Yes |
| GET | `/api/routes/{id}/` | Route detail | Yes |
| POST | `/api/routes/auto/` | Auto route recommendation (F03) | Yes |
| POST | `/api/routes/{id}/share/` | Create share link | Yes |
| POST | `/api/routes/{id}/fork/` | Fork route | Yes |
| GET | `/api/shared/{token}/` | View shared route | **No (AllowAny)** |
| POST | `/api/gps/log/` | Receive GPS log (every 30s) | Yes |
| POST | `/api/visits/{spot_id}/certify/` | Request GPS verification | Yes |
| GET | `/api/reviews/?spot_id=` | Spot review list | No |
| POST | `/api/reviews/` | Submit review (CERTIFIED only) | Yes |
| GET | `/api/health/` | Health check | No |

---

## Response Format

**Success**: DRF default format

**Error**:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "user-facing message",
    "detail": {}
  }
}
```

---

## KTO OpenAPI Integration

**Base URL**: `https://apis.data.go.kr/B551011/`
**Auth**: Query parameter `ServiceKey` (`KTO_API_KEY` from `.env`)

### Call Strategy
- **Prototype phase**: manual `python manage.py sync_spots` (no Celery)
- **Production phase**: Celery beat scheduled sync (spots: 24h / congestion: 6h)

### httpx Usage
- Use **sync client** (`httpx.Client()`) inside Celery tasks
- Do not use async — conflicts with Django's sync environment

### Error Handling
- Timeout: 3,000ms
- tenacity retry: max 3 attempts, exponential backoff
- Fallback on failure: Redis cache → if missing, return latest DB data

### Caching (production phase)
| Data | Refresh interval |
|------|-----------------|
| Spot base info | 24h (DB sync) |
| Congestion forecast | 6h |
| Other non-realtime responses | Redis TTL 60min |
