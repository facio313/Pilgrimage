# Pilgrimage — API 명세

---

## REST API 엔드포인트

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
| POST | `/api/auth/register` | 회원가입 | 불필요 |
| POST | `/api/auth/login` | 로그인 (JWT 발급) | 불필요 |
| POST | `/api/auth/refresh` | Access 토큰 갱신 | 불필요 |
| GET | `/api/spots/?theme=&lat=&lng=&radius=` | 관광지 목록 (반경 쿼리) | 불필요 |
| GET | `/api/spots/{id}/` | 관광지 상세 | 불필요 |
| POST | `/api/routes/` | 경로 저장 | 필요 |
| GET | `/api/routes/{id}/` | 경로 상세 | 필요 |
| POST | `/api/routes/auto/` | 자동 경로 추천 (F03) | 필요 |
| POST | `/api/routes/{id}/share/` | 공유 링크 생성 | 필요 |
| POST | `/api/routes/{id}/fork/` | 경로 복제 | 필요 |
| GET | `/api/shared/{token}/` | 공유 경로 조회 | **불필요 (AllowAny)** |
| POST | `/api/gps/log/` | GPS 로그 수신 (30초 간격) | 필요 |
| POST | `/api/visits/{spot_id}/certify/` | GPS 인증 판정 요청 | 필요 |
| GET | `/api/reviews/?spot_id=` | 관광지 후기 목록 | 불필요 |
| POST | `/api/reviews/` | 후기 작성 (CERTIFIED만 가능) | 필요 |
| GET | `/api/health/` | 헬스체크 | 불필요 |

---

## 응답 형식

**성공**: DRF 기본 형식

**실패**:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "사용자 메시지",
    "detail": {}
  }
}
```

---

## KTO OpenAPI 연동

**Base URL**: `https://apis.data.go.kr/B551011/`  
**인증**: Query Parameter `ServiceKey` (`.env`의 `KTO_API_KEY`)

### 호출 전략
- **프로토타입 단계**: `python manage.py sync_spots` 수동 실행 (Celery 없음)
- **배포 단계**: Celery beat로 자동 주기 실행 (24h / 혼잡도 6h)

### httpx 사용 방식
- Celery 태스크 내에서는 **동기 클라이언트** 사용 (`httpx.Client()`)
- async는 사용하지 않음 (Django 동기 환경과 충돌 방지)

### 에러 처리
- 타임아웃: 3,000ms
- tenacity 재시도: 최대 3회, exponential backoff
- 장애 시 fallback: Redis 캐시 → 없으면 DB 최신 데이터 반환

### 캐싱 (배포 단계)
| 데이터 | 갱신 주기 |
|--------|-----------|
| 관광지 기본 정보 | 24시간 (DB 동기화) |
| 혼잡도 예측 정보 | 6시간 |
| 기타 실시간성 불필요 응답 | Redis TTL 60분 |
