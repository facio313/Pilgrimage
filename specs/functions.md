# Pilgrimage — Feature Specs

> Ordered by priority. Use this file as the reference during implementation.

---

## F01 · Theme Selection (priority 1)

User selects one or more travel themes; returns a list of matching tourist spots.

- Themes (11): mixed, nature, heritage, urban, festival, leisure, shopping, food, camping, medical, family
- Theme key → `contentTypeId` mapping managed in `common/themes.py` as a Python dict constant
- camping / medical / family use separate KTO APIs (Gocamping, Medical Tourism, Barrier-free Travel)
- Region-specific themes are prioritized when a region is selected

**KTO API**
- Base list: KorService1 (Korean Tourism Info Service)
- Regional diversity: Regional Tourism Diversity
- Region-based: Municipal Tourism Info

---

## F02 · Route Builder — Floating Menu (priority 2)

Clicking a point on the Kakao map shows nearby spots in a floating menu. Selecting one auto-calculates the shortest route. Repeat to build the full route.

- PostGIS `ST_DWithin` spatial query within 5km radius
- Route algorithm: Nearest Neighbor TSP approximation (Python server-side)
- Transport mode weights applied per segment (linked to F07)
- High-congestion spots ranked lower in route order
- Route visualized as Kakao Maps Polyline

**KTO API**
- Nearby recommendations: Related Tourist Spots API
- Demand weighting: Regional Tourism Resource Demand
- Congestion avoidance: Tourist Spot Congestion Forecast

---

## F03 · Auto Route Recommendation (priority 3)

User inputs conditions; scoring engine builds the optimal route automatically.

**Input parameters**
- Number of spots (N), budget ceiling (KRW), minimum rating, max travel distance (km), operating hours filter, transport mode (F07)

**Scoring formula**
```
score = w1·review_score + w2·(1/cost) + w3·(1/distance) + w4·congestion_penalty
```
Weights w1–w4 differ per theme, managed as Python dataclass

**Rules**
- Operating hours filter: only include spots open on the selected date
- If budget exceeded, reduce spot count and retry

**KTO API**
- camping → Gocamping Info Service
- medical → Medical Tourism Info, Wellness Tourism Info
- eco → Eco-Tourism Info, Durunubi Info Service
- barrier-free → Barrier-free Travel Info
- pet → Pet-friendly Travel Service

---

## F04 · GPS Stay Verification — 30-Min Rule (priority 4)

30+ minutes within 200m of a spot grants CERTIFIED status. Only certified users may write reviews.

| Parameter | Value |
|-----------|-------|
| Radius | 200m |
| Min stay | 30 min |
| Grace period | 10 min (resume if user returns within 10 min) |
| Log interval | 30 sec |
| Spoof detection | Speed > 200km/h between consecutive logs → REJECTED |

**Status**: `UNVISITED` / `CERTIFIED` / `REJECTED`

**Web platform constraints**
- Location only available when browser tab is in foreground
- HTTPS required (Geolocation API enforces Secure Context)
- Page Visibility API pauses stay timer when tab goes inactive
- `beforeunload` warning shown when navigating away during tracking

---

## F05 · Review System — GPS-Verified Only (priority 5)

Only users with `VisitLog.status == "CERTIFIED"` can submit reviews. Eliminates fake/ad reviews.

**Review fields**
- Rating (1–5), text body, costs (entrance fee / food / other), visit date (auto from visit_log FK), up to 5 photos

**Display rules**
- Floating menu: sorted by rating (high to low)
- GPS-verified badge shown
- Per-spot average cost and average stay time computed automatically

Review data feeds into F03 scoring engine (`review_score`).

---

## F06 · Route Save / Share / Fork (priority 6)

Save completed routes and share or fork them at the route level (not just pins or text).

- Share link: UUID-based shortlink (`/shared/:token`) — no login required
- Public / private toggle
- Fork preserves `fork_from_id` reference to original
- Visit verification status (complete/incomplete) shown on route
- Memoir mode: past trips can also be saved as routes

---

## F07 · Transport Mode & Cost Calculation (priority 7)

Selecting a transport mode recalculates the route and estimates travel cost.

**Modes**: car, bus, train, walking, bicycle, mixed

**Cost rules**
- Car: `distance(km) ÷ 12(km/L) × 1,700(KRW/L)`
- Public transit: ~100 KRW per km
- Walking / bicycle: 0 KRW

---

## F08 · Spot Detail Page (priority 8)

Per-spot detail page: description, audio guide, photos, reviews, cost stats.

**KTO API**
- Audio guide: Tourist Spot Audio Guide Info
- Photos: Tourism Photo Info

---

## F09 · International User Support — Multilingual (priority 9, long-term)

Expand service to inbound travelers using KTO foreign-language tourism APIs.

- Languages: English, Japanese, Chinese (Simplified/Traditional), Russian, Spanish, French, German
