import { type CSSProperties, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useKakaoMap } from '../hooks/useKakaoMap';
import { listSpots, getNearbyRecommend, upsertSpot, type Spot, type NearbySpot } from '../api/spots';
import { getDirections, formatDistance, formatDuration, type DirectionsResult } from '../api/directions';
import { login, register } from '../api/auth';
import { apiClient } from '../api/client';
import { useAuthStore } from '../store/auth';
import { useRouteDraftStore } from '../store/route';

const SEOUL_CITY_HALL = { lat: 37.5666103, lng: 126.9783882 };
const SEARCH_RADIUS_M = 10_000;
const SAVED_POINT_HIT_RADIUS_M = 40;
const COMPACT_NAV_MAX_WIDTH = 1024;
const DRAWER_ANIMATION_MS = 280;
const DRAWER_EDGE_GAP_PX = 16;

interface PopoverExtra {
  spot?: Spot;
  phone?: string;
  category?: string;
  categoryCode?: string;
  placeUrl?: string;
}

interface PointOverlayRecord {
  overlay: any;
  ringOverlay: any | null;
  lat: number;
  lng: number;
  name: string;
  address: string;
  icon: string;
  rating: number;
  extra?: PopoverExtra;
}

interface CachedPopoverData {
  lat: number;
  lng: number;
  name: string;
  address: string;
  extra?: PopoverExtra;
}

interface OrderedPoint {
  lat: number;
  lng: number;
  name: string;
  icon: string;
  address: string;
  rating: number;
}

interface RouteGroup {
  id: string;
  name: string;
  points: OrderedPoint[];
}

export function MapPage() {
  const navigate = useNavigate();
  const { theme, spotIds, addSpot, removeSpot } = useRouteDraftStore();
  const { accessToken, userEmail, userNickname, clear } = useAuthStore();
  const [canUseCompactNav, setCanUseCompactNav] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth <= COMPACT_NAV_MAX_WIDTH : false
  );
  const [isRouteAdjustOpen, setIsRouteAdjustOpen] = useState(false);
  const [isRouteAnalysisOpen, setIsRouteAnalysisOpen] = useState(false);
  const [orderedPoints, setOrderedPoints] = useState<OrderedPoint[]>([]);
  const [routeGroups, setRouteGroups] = useState<RouteGroup[]>([
    { id: 'route-1', name: '경로 1', points: [] },
  ]);
  const [activeRouteId, setActiveRouteId] = useState('route-1');
  const nextGroupNumRef = useRef(2);
  const { containerRef, map, error } = useKakaoMap({ center: SEOUL_CITY_HALL });

  useEffect(() => {
    const onResize = () => {
      setCanUseCompactNav(window.innerWidth <= COMPACT_NAV_MAX_WIDTH);
    };
    onResize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const { data: spots = [], isLoading } = useQuery({
    queryKey: ['spots', theme],
    queryFn: () =>
      listSpots({
        theme: theme ?? undefined,
        lat: SEOUL_CITY_HALL.lat,
        lng: SEOUL_CITY_HALL.lng,
        radius: SEARCH_RADIUS_M,
      }),
    enabled: !!map && !!theme,
  });

  const markersRef = useRef<any[]>([]);
  const overlayRef = useRef<any>(null);
  const pointOverlaysRef = useRef<PointOverlayRecord[]>([]);
  const popoverCacheRef = useRef<Map<string, CachedPopoverData>>(new Map());
  const spotCoordsRef = useRef<Map<string, { lat: number; lng: number }>>(new Map());
  const nearbyPlaceCacheRef = useRef<Map<string, any | null>>(new Map());
  const reviewsCacheRef = useRef<Map<string, any[]>>(new Map());

  const stopMapEvent = (event: Event) => {
    event.stopPropagation();
    window.kakao?.maps?.event?.preventMap?.();
  };

  const coordinateKey = (lat: number, lng: number) => `coord:${lat.toFixed(4)},${lng.toFixed(4)}`;
  const addressKey = (address: string) => {
    const normalized = address.trim().replace(/\s+/g, ' ').toLowerCase();
    return normalized ? `addr:${normalized}` : '';
  };
  const getCacheKey = (lat: number, lng: number, address: string) =>
    addressKey(address) || coordinateKey(lat, lng);

  const distanceMeters = (aLat: number, aLng: number, bLat: number, bLng: number) => {
    const toRad = (value: number) => (value * Math.PI) / 180;
    const earthRadiusM = 6_371_000;
    const dLat = toRad(bLat - aLat);
    const dLng = toRad(bLng - aLng);
    const lat1 = toRad(aLat);
    const lat2 = toRad(bLat);
    const h =
      Math.sin(dLat / 2) ** 2 +
      Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
    return 2 * earthRadiusM * Math.asin(Math.sqrt(h));
  };

  const findPointAt = (lat: number, lng: number) =>
    pointOverlaysRef.current.find((p) => p.lat === lat && p.lng === lng);

  const findSavedPointNear = (lat: number, lng: number) =>
    pointOverlaysRef.current.find(
      (p) => distanceMeters(lat, lng, p.lat, p.lng) <= SAVED_POINT_HIT_RADIUS_M
    );

  const cachePopover = (lat: number, lng: number, name: string, address: string, extra?: PopoverExtra) => {
    const payload = { lat, lng, name, address, extra };
    popoverCacheRef.current.set(coordinateKey(lat, lng), payload);
    const key = addressKey(address);
    if (key) popoverCacheRef.current.set(key, payload);
  };

  const getCachedPopover = (lat: number, lng: number, address = '') => {
    const byAddress = address ? popoverCacheRef.current.get(addressKey(address)) : undefined;
    return byAddress || popoverCacheRef.current.get(coordinateKey(lat, lng));
  };

  const removePointAt = (lat: number, lng: number) => {
    const idx = pointOverlaysRef.current.findIndex((p) => p.lat === lat && p.lng === lng);
    if (idx !== -1) {
      pointOverlaysRef.current[idx].overlay.setMap(null);
      if (pointOverlaysRef.current[idx].ringOverlay) {
        pointOverlaysRef.current[idx].ringOverlay.setMap(null);
      }
      pointOverlaysRef.current.splice(idx, 1);
      setOrderedPoints((prev) => prev.filter((p) => !(p.lat === lat && p.lng === lng)));
    }
  };

  const placePointOverlay = (lat: number, lng: number, icon: string, rating: number, name: string, address: string, extra?: PopoverExtra) => {
    if (!map) return;
    const kakao = window.kakao;
    const position = new kakao.maps.LatLng(lat, lng);
    const ratio = Math.min(rating / 5, 1);
    const degrees = ratio * 360;
    const el = document.createElement('div');
    el.className = 'point-marker';
    el.innerHTML = `
      <span class="point-marker__ring" style="background: conic-gradient(#f5c518 0deg ${degrees}deg, #d8d8d8 ${degrees}deg 360deg)">
        <span class="point-marker__icon">${icon}</span>
      </span>
    `;
    ['click', 'mousedown', 'pointerdown', 'touchstart'].forEach((eventName) => {
      el.addEventListener(eventName, stopMapEvent);
    });
    el.addEventListener('click', () => {
      showPopover(position, name, address, extra);
    });
    const overlay = new kakao.maps.CustomOverlay({
      content: el,
      position,
      yAnchor: 0.5,
      xAnchor: 0.5,
      zIndex: 15,
      clickable: true,
    });
    overlay.setMap(map);
    cachePopover(lat, lng, name, address, extra);
    pointOverlaysRef.current.push({ overlay, ringOverlay: null, lat, lng, name, address, icon, rating, extra });
  };

  const createPointMarker = (position: any, icon: string, rating: number, name: string, address: string, extra?: PopoverExtra) => {
    const lat = position.getLat();
    const lng = position.getLng();
    placePointOverlay(lat, lng, icon, rating, name, address, extra);
    setOrderedPoints((prev) => [...prev, { lat, lng, name, icon, address, rating }]);
    createNearbyRing(lat, lng);
  };

  const closeOverlay = () => {
    overlayRef.current?.setMap(null);
    overlayRef.current = null;
  };

  const clearAllPoints = () => {
    pointOverlaysRef.current.forEach((p) => {
      p.overlay.setMap(null);
      if (p.ringOverlay) p.ringOverlay.setMap(null);
    });
    pointOverlaysRef.current = [];
    drawLinesRef.current.forEach((l) => l.setMap(null));
    drawLinesRef.current = [];
    lastDrawPointRef.current = null;
  };

  const switchGroup = (newGroupId: string) => {
    if (newGroupId === activeRouteId) return;
    setRouteGroups((prev) =>
      prev.map((g) => (g.id === activeRouteId ? { ...g, points: orderedPoints } : g))
    );
    clearAllPoints();
    const newGroup = routeGroups.find((g) => g.id === newGroupId);
    const newPoints = newGroup?.points ?? [];
    setActiveRouteId(newGroupId);
    setOrderedPoints(newPoints);
    newPoints.forEach((p) => placePointOverlay(p.lat, p.lng, p.icon, p.rating, p.name, p.address));
  };

  const addNewGroup = () => {
    const num = nextGroupNumRef.current++;
    const id = `route-${num}`;
    setRouteGroups((prev) => {
      const saved = prev.map((g) =>
        g.id === activeRouteId ? { ...g, points: orderedPoints } : g
      );
      return [...saved, { id, name: `경로 ${num}`, points: [] }];
    });
    clearAllPoints();
    setActiveRouteId(id);
    setOrderedPoints([]);
  };

  const CATEGORY_ICONS: Record<string, string> = {
    SW8: '🚇', AT4: '🏛️', CT1: '🎭', FD6: '🍽️', CE7: '☕',
    HP8: '🏥', PK6: '🅿️', OL7: '⛽', SC4: '🏫', BK9: '🏦',
    MT1: '🛒', CS2: '🏪', AD5: '🏨', PM9: '💊',
  };
  const CATEGORY_LABELS: Record<string, string> = {
    SW8: '지하철역', AT4: '관광명소', CT1: '문화시설', FD6: '음식점', CE7: '카페',
    HP8: '병원', PK6: '주차장', OL7: '주유소', SC4: '학교', BK9: '은행',
    MT1: '대형마트', CS2: '편의점', AD5: '숙박', PM9: '약국',
  };

  const THEME_ICONS: Record<string, string> = {
    nature: '🌿', heritage: '🏛️', urban: '🏙️', festival: '🎪', leisure: '🎡',
    shopping: '🛍️', food: '🍽️', camping: '⛺', medical: '🏥', family: '👨‍👩‍👧', mixed: '📍',
  };
  const CATEGORY_TO_ICON: Record<string, string> = {
    '음식점': '🍽️', '카페': '☕', '전통시장': '🛍️', '쇼핑': '🛍️', '문화재': '🏛️',
    '공원': '🌿', '관광지': '📍', '도시공원': '🏙️', '전망대': '👀', '등산로': '⛰️',
    '갤러리': '🎨', '전통마을': '🏛️', '박물관': '🏛️', '자연': '🌿', '서점': '📚',
    '문화시설': '🎭', '레저': '🎡',
  };

  const getSpotIcon = (spot: NearbySpot) => {
    if (spot.category && CATEGORY_TO_ICON[spot.category]) return CATEGORY_TO_ICON[spot.category];
    for (const tag of spot.theme_tags) {
      if (THEME_ICONS[tag]) return THEME_ICONS[tag];
    }
    return '📍';
  };

  const RING_RADIUS_PX = 118;
  const RING_SLOT_BEARINGS = [0, 45, 90, 135, 180, 225, 270, 315];

  const createNearbyRing = (centerLat: number, centerLng: number): { overlay: any } | null => {
    if (!map) return null;
    const kakao = window.kakao;

    getNearbyRecommend({ lat: centerLat, lng: centerLng, theme: theme || undefined })
      .then((nearby) => {
        if (!nearby.length) return;

        const el = document.createElement('div');
        el.className = 'nearby-ring';
        ['click', 'mousedown', 'pointerdown', 'touchstart'].forEach((ev) => {
          el.addEventListener(ev, stopMapEvent);
        });

        nearby.slice(0, RING_SLOT_BEARINGS.length).forEach((spot, index) => {
          const bearingRad = (RING_SLOT_BEARINGS[index] * Math.PI) / 180;
          const x = RING_RADIUS_PX * Math.sin(bearingRad);
          const y = -RING_RADIUS_PX * Math.cos(bearingRad);

          const item = document.createElement('div');
          item.className = 'nearby-ring__item';
          item.style.setProperty('--x', `${Math.round(x)}px`);
          item.style.setProperty('--y', `${Math.round(y)}px`);

          const icon = getSpotIcon(spot);
          const score = Number(spot.avg_review_score).toFixed(1);
          const degrees = Math.round(Math.min(Number(spot.avg_review_score) / 5, 1) * 360);

          item.innerHTML = `
            <span class="nearby-ring__ring" style="background: conic-gradient(#f5c518 0deg ${degrees}deg, #d8d8d8 ${degrees}deg 360deg)">
              <span class="nearby-ring__bubble">${icon}</span>
            </span>
            <span class="nearby-ring__name">${spot.name.length > 6 ? spot.name.slice(0, 6) + '…' : spot.name}</span>
            <span class="nearby-ring__score">⭐ ${score}</span>
          `;

          ['click', 'mousedown', 'pointerdown', 'touchstart'].forEach((ev) => {
            item.addEventListener(ev, stopMapEvent);
          });

          item.addEventListener('click', () => {
            const pos = new kakao.maps.LatLng(spot.lat, spot.lng);
            map!.panTo(pos);
            setTimeout(() => {
              showPopover(pos, spot.name, spot.address, { spot: spot as unknown as Spot });
            }, 400);
          });

          el.appendChild(item);
        });

        const ringOvl = new kakao.maps.CustomOverlay({
          content: el,
          position: new kakao.maps.LatLng(centerLat, centerLng),
          yAnchor: 0.5,
          xAnchor: 0.5,
          zIndex: 12,
          clickable: true,
        });
        ringOvl.setMap(map);

        const record = pointOverlaysRef.current.find(
          (p) => p.lat === centerLat && p.lng === centerLng
        );
        if (record) record.ringOverlay = ringOvl;
      })
      .catch((err) => {
        console.error('[Pilgrimage] nearby recommend error:', err);
      });

    return null;
  };

  const showPopover = (position: any, name: string, address: string, extra?: PopoverExtra) => {
    if (!map) return;
    const kakao = window.kakao;
    closeOverlay();

    const spot = extra?.spot;
    const el = document.createElement('div');
    el.className = 'spot-popover';
    ['click', 'mousedown', 'pointerdown', 'touchstart', 'dblclick'].forEach((eventName) => {
      el.addEventListener(eventName, stopMapEvent);
    });

    const icon = extra?.categoryCode ? CATEGORY_ICONS[extra.categoryCode] || '📍' : '📍';
    const categoryLabel = extra?.categoryCode ? CATEGORY_LABELS[extra.categoryCode] || extra?.category || '' : extra?.category || '';
    const scoreHtml = spot ? `<p class="spot-popover__score">평점 ${Number(spot.avg_review_score).toFixed(1)}</p>` : '';
    const categoryHtml = categoryLabel ? `<span class="spot-popover__badge">${icon} ${categoryLabel}</span>` : '';
    const phoneHtml = extra?.phone ? `<p class="spot-popover__phone">📞 ${extra.phone}</p>` : '';
    const hasPoint = !!findPointAt(position.getLat(), position.getLng());

    el.innerHTML = `
      <button class="spot-popover__close" aria-label="닫기">&times;</button>
      <div class="spot-popover__photo-slot"><div class="spot-popover__photo-placeholder"></div></div>
      ${categoryHtml}
      <div class="spot-popover__name-row">
        <strong class="spot-popover__name" data-action="detail">${name}</strong><button data-action="visit" class="spot-popover__visit-badge">✓</button>
      </div>
      <p class="spot-popover__addr">${address}</p>
      ${phoneHtml}${scoreHtml}
      <div class="spot-popover__google"><span class="spot-popover__info-skel"></span></div>
      <div class="spot-popover__reviews"></div>
      <div class="spot-popover__links"></div>
      <div class="spot-popover__btn-col">
        <button data-action="set-point" class="spot-popover__btn-primary">${hasPoint ? '지점 해제' : '지점 설정'}</button>
        <div class="spot-popover__btn-row">
          <button data-action="route" class="spot-popover__btn-primary">경로 추가</button>
          <button data-action="draw-line" class="spot-popover__btn-primary">경로 그리기</button>
        </div>
      </div>
      <div class="spot-popover__tail"></div>
    `;

    let placeRating = spot ? Number(spot.avg_review_score) || 0 : 0;

    const lat = position.getLat();
    const lng = position.getLng();
    const nearbyCacheKey = getCacheKey(lat, lng, address);
    const searchQuery = encodeURIComponent(`${name} ${address}`.trim());
    const placeLookupKey = `google:v2:${nearbyCacheKey}|${searchQuery}`;
    cachePopover(lat, lng, name, address, extra);

    const isDbSpot = !!(spot && spot.id);
    const linksSlot = el.querySelector('.spot-popover__links');
    const renderMapLinks = (place?: any | null) => {
      if (!linksSlot) return;
      const googleMapsUrl = place?.googleMapsUri || `https://www.google.com/maps/search/?api=1&query=${searchQuery}`;
      const kakaoMapsUrl = extra?.placeUrl || `https://map.kakao.com/link/search/${searchQuery}`;
      linksSlot.innerHTML = [
        `<a class="spot-popover__map-link" href="${googleMapsUrl}" target="_blank" rel="noopener">구글맵에서 보기</a>`,
        `<a class="spot-popover__map-link" href="${kakaoMapsUrl}" target="_blank" rel="noopener">카카오맵에서 보기</a>`,
      ].join('');
    };
    renderMapLinks();

    const overlay = new kakao.maps.CustomOverlay({
      content: el,
      position,
      yAnchor: 1.04,
      xAnchor: 0.5,
      zIndex: 20,
      clickable: true,
    });
    overlay.setMap(map);
    overlayRef.current = overlay;

    const syncPopoverPosition = () => overlay.setPosition(position);
    window.requestAnimationFrame(syncPopoverPosition);

    const renderGooglePlaceInfo = (place: any | null) => {
      const googleSlot = el.querySelector('.spot-popover__google');
      if (!googleSlot) return;

      if (!place?.placeId) {
        googleSlot.innerHTML = '<span class="spot-popover__no-info">구글 정보를 가져올 수 없습니다</span>';
        return;
      }

      if (place.rating) placeRating = place.rating;
      googleSlot.innerHTML = `<span class="spot-popover__rating-btn" data-place-id="${place.placeId}">${place.rating ? `⭐ ${place.rating}${place.userRatingCount ? ` (${place.userRatingCount})` : ''} · ` : ''}구글 리뷰 보기 ▾</span>`;

      const ratingBtn = googleSlot.querySelector('.spot-popover__rating-btn');
      const reviewSlot = el.querySelector('.spot-popover__reviews');
      if (!ratingBtn || !reviewSlot) return;

      ratingBtn.addEventListener('click', (ev) => {
        ev.stopPropagation();
        if (reviewSlot.children.length > 0) {
          reviewSlot.innerHTML = '';
          return;
        }
        const cachedReviews = reviewsCacheRef.current.get(place.placeId);
        if (cachedReviews) {
          reviewSlot.innerHTML = renderReviews(cachedReviews);
          return;
        }
        reviewSlot.innerHTML = '<p class="spot-popover__review-loading">리뷰 불러오는 중...</p>';
        apiClient.get('/places/reviews/', { params: { place_id: place.placeId } }).then((revRes) => {
          const reviews = revRes.data?.reviews || [];
          reviewsCacheRef.current.set(place.placeId, reviews);
          if (!reviews.length) {
            reviewSlot.innerHTML = '<p class="spot-popover__review-empty">등록된 리뷰가 없습니다</p>';
            return;
          }
          reviewSlot.innerHTML = renderReviews(reviews);
        }).catch(() => {
          reviewSlot.innerHTML = '<p class="spot-popover__review-empty">리뷰를 가져올 수 없습니다</p>';
        });
      });
    };

    const applyNearbyPlace = (place: any | null) => {
      const photoSlot = el.querySelector('.spot-popover__photo-slot');
      if (photoSlot && place?.photoUrl) {
        const img = document.createElement('img');
        img.className = 'spot-popover__photo';
        img.alt = place.name ?? '';
        img.style.opacity = '0';
        img.addEventListener('load', () => {
          window.requestAnimationFrame(() => { img.style.opacity = '1'; });
        }, { once: true });
        img.addEventListener('error', () => {
          img.replaceWith(document.createElement('div'));
          const ph = photoSlot.querySelector('div');
          if (ph) ph.className = 'spot-popover__photo-placeholder';
        }, { once: true });
        img.src = place.photoUrl;
        photoSlot.innerHTML = '';
        photoSlot.appendChild(img);
      }
      renderGooglePlaceInfo(place);
      renderMapLinks(place);
    };

    if (nearbyPlaceCacheRef.current.has(placeLookupKey)) {
      applyNearbyPlace(nearbyPlaceCacheRef.current.get(placeLookupKey) ?? null);
    } else {
      apiClient.get('/places/nearby/', {
        params: { lat, lng, query: `${name} ${address}`.trim() },
      }).then((res) => {
        const place = res.data?.results?.[0] ?? null;
        if (place) nearbyPlaceCacheRef.current.set(placeLookupKey, place);
        applyNearbyPlace(place);
      }).catch(() => {
        applyNearbyPlace(null);
      });
    }


    el.querySelector('.spot-popover__close')!.addEventListener('click', closeOverlay);

    el.querySelector('[data-action="set-point"]')!.addEventListener('click', () => {
      const lat = position.getLat();
      const lng = position.getLng();
      if (findPointAt(lat, lng)) {
        removePointAt(lat, lng);
      } else {
        pointOverlaysRef.current.forEach((p) => {
          if (p.ringOverlay) {
            p.ringOverlay.setMap(null);
            p.ringOverlay = null;
          }
        });
        createPointMarker(position, icon, placeRating, name, address, extra);
      }
      closeOverlay();
    });

    const routeBtn = el.querySelector('[data-action="route"]') as HTMLButtonElement;
    if (spot && inRoute(spot.id)) {
      routeBtn.textContent = '경로 제거';
      routeBtn.classList.remove('spot-popover__btn-primary');
      routeBtn.classList.add('spot-popover__btn-secondary');
    }
    const visitBadge = el.querySelector('[data-action="visit"]') as HTMLElement;
    if (!isAuthed) {
      routeBtn.style.display = 'none';
      visitBadge.style.display = 'none';
    } else if (spot) {
      apiClient.get(`/visits/${spot.id}/status/`)
        .then((res) => {
          if (res.data?.certified) visitBadge.classList.add('certified');
        })
        .catch(() => {});
    }

    const ensureSpot = async (): Promise<Spot | null> => {
      if (spot) return spot;
      try {
        let external_id: string | undefined;
        if (extra?.placeUrl) {
          const match = extra.placeUrl.match(/\/(\d+)$/);
          if (match) external_id = `kakao:${match[1]}`;
        }
        return await upsertSpot({ name, lat, lng, address, category: extra?.category, external_id });
      } catch {
        return null;
      }
    };

    el.querySelector('[data-action="detail"]')!.addEventListener('click', async () => {
      const s = await ensureSpot();
      if (s) navigate(`/spot/${s.id}`);
    });
    routeBtn.addEventListener('click', async () => {
      const s = await ensureSpot();
      if (s) {
        if (inRoute(s.id)) {
          removeSpot(s.id);
        } else {
          addSpot(s.id);
          spotCoordsRef.current.set(s.id, { lat, lng });
        }
      }
      closeOverlay();
    });
    el.querySelector('[data-action="draw-line"]')!.addEventListener('click', () => {
      const currentLat = position.getLat();
      const currentLng = position.getLng();
      if (lastDrawPointRef.current) {
        const kakao = window.kakao;
        const line = new kakao.maps.Polyline({
          map,
          path: [
            new kakao.maps.LatLng(lastDrawPointRef.current.lat, lastDrawPointRef.current.lng),
            new kakao.maps.LatLng(currentLat, currentLng),
          ],
          strokeWeight: 3,
          strokeColor: '#34a853',
          strokeOpacity: 0.9,
          strokeStyle: 'dashed',
        });
        drawLinesRef.current.push(line);
      }
      lastDrawPointRef.current = { lat: currentLat, lng: currentLng };
      closeOverlay();
    });

    el.querySelector('[data-action="visit"]')!.addEventListener('click', async () => {
      const s = await ensureSpot();
      if (s) navigate(`/visit/${s.id}`);
    });

  };

  const renderReviews = (reviews: any[]) => {
    if (!reviews.length) return '<p class="spot-popover__review-empty">리뷰가 없습니다</p>';
    return reviews.map((rv: any) =>
      `<div class="spot-popover__review">
        <div class="spot-popover__review-header">
          <strong>${rv.author}</strong>
          <span>${'⭐'.repeat(rv.rating || 0)}</span>
          <span class="spot-popover__review-time">${rv.relativeTime}</span>
        </div>
        <p>${rv.text?.length > 80 ? rv.text.slice(0, 80) + '…' : rv.text}</p>
      </div>`
    ).join('');
  };

  const renderOurReviews = (reviews: any[]) => {
    if (!reviews.length) return '<p class="spot-popover__review-empty">리뷰가 없습니다</p>';
    return reviews.map((rv: any) =>
      `<div class="spot-popover__review">
        <div class="spot-popover__review-header">
          <strong>${rv.user_nickname || '익명'}</strong>
          <span>${'⭐'.repeat(rv.rating || 0)}</span>
        </div>
        <p>${(rv.body || '').length > 80 ? rv.body.slice(0, 80) + '…' : rv.body || ''}</p>
      </div>`
    ).join('');
  };

  const openOverlay = (spot: Spot) => {
    const kakao = window.kakao;
    const position = new kakao.maps.LatLng(spot.lat, spot.lng);
    showPopover(position, spot.name, spot.address || '', { spot });
  };

  useEffect(() => {
    if (!map) return;
    const kakao = window.kakao;
    const places = new kakao.maps.services.Places();

    const geocoder = new kakao.maps.services.Geocoder();
    const CATEGORIES = ['SW8', 'AT4', 'CT1', 'FD6', 'CE7', 'HP8', 'PK6', 'OL7', 'SC4', 'BK9', 'MT1', 'CS2', 'AD5', 'PM9'];

    const onClick = (_mouseEvent: any) => {
      const latlng = _mouseEvent.latLng;
      const clickedLat = latlng.getLat();
      const clickedLng = latlng.getLng();
      const savedPoint = findSavedPointNear(clickedLat, clickedLng);
      if (savedPoint) {
        showPopover(
          new kakao.maps.LatLng(savedPoint.lat, savedPoint.lng),
          savedPoint.name,
          savedPoint.address,
          savedPoint.extra
        );
        return;
      }

      const cachedByCoordinate = getCachedPopover(clickedLat, clickedLng);
      if (cachedByCoordinate) {
        showPopover(
          new kakao.maps.LatLng(cachedByCoordinate.lat, cachedByCoordinate.lng),
          cachedByCoordinate.name,
          cachedByCoordinate.address,
          cachedByCoordinate.extra
        );
        return;
      }

      let bestPlace: any = null;
      let resolved = 0;

      const tryShow = (roadAddr = '', jibunAddr = '') => {
        const cachedByAddress = getCachedPopover(clickedLat, clickedLng, roadAddr || jibunAddr);
        if (cachedByAddress) {
          showPopover(
            new kakao.maps.LatLng(cachedByAddress.lat, cachedByAddress.lng),
            cachedByAddress.name,
            cachedByAddress.address,
            cachedByAddress.extra
          );
          return;
        }

        if (bestPlace) {
          showPopover(latlng, bestPlace.place_name, bestPlace.road_address_name || bestPlace.address_name, {
            phone: bestPlace.phone,
            category: bestPlace.category_group_name,
            categoryCode: bestPlace.category_group_code,
            placeUrl: bestPlace.place_url,
          });
        } else {
          showPopover(latlng, roadAddr || jibunAddr, roadAddr ? jibunAddr : '');
        }
      };

      const searchOpts = { location: latlng, radius: 50, size: 1, sort: kakao.maps.services.SortBy.DISTANCE };

      geocoder.coord2Address(clickedLng, clickedLat, (addrResult: any[], addrStatus: string) => {
        const addr = addrStatus === kakao.maps.services.Status.OK && addrResult.length > 0 ? addrResult[0] : null;
        const roadAddr = addr?.road_address?.address_name || '';
        const jibunAddr = addr?.address?.address_name || '';
        const cachedByAddress = getCachedPopover(clickedLat, clickedLng, roadAddr || jibunAddr);
        if (cachedByAddress) {
          showPopover(
            new kakao.maps.LatLng(cachedByAddress.lat, cachedByAddress.lng),
            cachedByAddress.name,
            cachedByAddress.address,
            cachedByAddress.extra
          );
          return;
        }

        CATEGORIES.forEach((code) => {
          places.categorySearch(code, (result: any[], status: string) => {
            if (status === kakao.maps.services.Status.OK && result.length > 0) {
              const place = result[0];
              const dist = parseFloat(place.distance);
              if (!bestPlace || dist < parseFloat(bestPlace.distance)) {
                bestPlace = place;
              }
            }
            resolved++;
            if (resolved === CATEGORIES.length) tryShow(roadAddr, jibunAddr);
          }, searchOpts);
        });
      });
    };

    kakao.maps.event.addListener(map, 'click', onClick);
    return () => kakao.maps.event.removeListener(map, 'click', onClick);
  }, [map]);

  useEffect(() => {
    if (!map) return;
    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];
    const kakao = window.kakao;
    spots.forEach((s) => {
      const marker = new kakao.maps.Marker({
        map,
        position: new kakao.maps.LatLng(s.lat, s.lng),
        title: s.name,
      });
      kakao.maps.event.addListener(marker, 'click', () => openOverlay(s));
      markersRef.current.push(marker);
    });
    return () => {
      markersRef.current.forEach((m) => m.setMap(null));
      markersRef.current = [];
      if (overlayRef.current) {
        overlayRef.current.setMap(null);
        overlayRef.current = null;
      }
    };
  }, [map, spots]);

  const polylineRef = useRef<any>(null);
  const setPointsPolylineRef = useRef<any>(null);
  const lastDrawPointRef = useRef<{ lat: number; lng: number } | null>(null);
  const drawLinesRef = useRef<any[]>([]);
  const selectedSpotsOrdered = useMemo(
    () =>
      spotIds
        .map((id) => {
          const fromList = spots.find((s) => s.id === id);
          if (fromList) return fromList;
          const coord = spotCoordsRef.current.get(id);
          return coord ? ({ id, lat: coord.lat, lng: coord.lng } as unknown as Spot) : null;
        })
        .filter((s): s is Spot => !!s),
    [spotIds, spots]
  );
  useEffect(() => {
    if (!map) return;
    if (polylineRef.current) {
      polylineRef.current.setMap(null);
      polylineRef.current = null;
    }
    if (selectedSpotsOrdered.length < 2) return;
    const kakao = window.kakao;
    polylineRef.current = new kakao.maps.Polyline({
      map,
      path: selectedSpotsOrdered.map((s) => new kakao.maps.LatLng(s.lat, s.lng)),
      strokeWeight: 4,
      strokeColor: '#1a73e8',
      strokeOpacity: 0.8,
    });
  }, [map, selectedSpotsOrdered]);

  const [directionsInfo, setDirectionsInfo] = useState<DirectionsResult | null>(null);
  const [directionsLoading, setDirectionsLoading] = useState(false);
  const directionsAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!map) return;

    // Clean up previous polyline
    if (setPointsPolylineRef.current) {
      setPointsPolylineRef.current.setMap(null);
      setPointsPolylineRef.current = null;
    }

    // Abort any in-flight directions request
    if (directionsAbortRef.current) {
      directionsAbortRef.current.abort();
      directionsAbortRef.current = null;
    }

    if (orderedPoints.length < 2) {
      setDirectionsInfo(null);
      return;
    }

    const kakao = window.kakao;

    // Draw fallback straight line immediately
    setPointsPolylineRef.current = new kakao.maps.Polyline({
      map,
      path: orderedPoints.map((p) => new kakao.maps.LatLng(p.lat, p.lng)),
      strokeWeight: 3,
      strokeColor: '#ff6b35',
      strokeOpacity: 0.4,
      strokeStyle: 'dashed',
    });

    // Fetch road directions
    const abortCtrl = new AbortController();
    directionsAbortRef.current = abortCtrl;
    setDirectionsLoading(true);

    const origin = { lat: orderedPoints[0].lat, lng: orderedPoints[0].lng };
    const destination = {
      lat: orderedPoints[orderedPoints.length - 1].lat,
      lng: orderedPoints[orderedPoints.length - 1].lng,
    };
    const waypoints = orderedPoints.length > 2
      ? orderedPoints.slice(1, -1).map((p) => ({ lat: p.lat, lng: p.lng }))
      : undefined;

    getDirections(origin, destination, waypoints, 'DISTANCE')
      .then((result) => {
        if (abortCtrl.signal.aborted) return;

        // Remove fallback dashed line
        if (setPointsPolylineRef.current) {
          setPointsPolylineRef.current.setMap(null);
        }

        // Draw road-following polyline
        setPointsPolylineRef.current = new kakao.maps.Polyline({
          map,
          path: result.polyline.map((c) => new kakao.maps.LatLng(c.lat, c.lng)),
          strokeWeight: 5,
          strokeColor: '#ff6b35',
          strokeOpacity: 0.9,
        });

        setDirectionsInfo(result);
      })
      .catch((err) => {
        if (abortCtrl.signal.aborted) return;
        console.warn('[Pilgrimage] Directions API failed, keeping straight line:', err);
        setDirectionsInfo(null);
      })
      .finally(() => {
        if (!abortCtrl.signal.aborted) setDirectionsLoading(false);
      });

    return () => {
      abortCtrl.abort();
    };
  }, [map, orderedPoints]);

  if (error) {
    return <div style={{ padding: 16, color: '#c00' }}>지도를 불러오지 못했습니다: {error.message}</div>;
  }

  const isAuthed = !!accessToken;
  const isCompact = isAuthed && canUseCompactNav;
  const overlayClass = `map-overlay ${isCompact ? 'compact' : 'expanded'} ${isAuthed ? 'with-menu' : 'with-form'}`;

  const inRoute = (id: string) => spotIds.includes(id);

  return (
    <div style={{ position: 'relative', height: '100vh', width: '100%', overflow: 'hidden' }}>
      <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />

      <div className={overlayClass}>
        <header className="map-header">
          <div className="map-header__stage" key={isAuthed ? 'menu' : 'auth'}>
            {isAuthed ? (
              <MenuRow
                isCompact={isCompact}
                map={map}
                userEmail={userEmail}
                userNickname={userNickname}
                routeGroups={routeGroups}
                activeRouteId={activeRouteId}
                spotCount={spotIds.length}
                onSwitchGroup={switchGroup}
                onAddGroup={addNewGroup}
                onTheme={() => navigate('/themes')}
                onAuto={() => navigate('/route/auto')}
                onSave={() => navigate('/route/save')}
                onLogout={clear}
                onRouteAdjust={() => setIsRouteAdjustOpen((v) => !v)}
                onRouteAnalysis={() => setIsRouteAnalysisOpen((v) => !v)}
              />
            ) : (
              <AuthInline />
            )}
          </div>
        </header>
        {isAuthed && <SearchBar map={map} />}
        {isAuthed && !isCompact && (
          <div className="map-toolbar">
            <div className="map-toolbar__left">
              <button onClick={() => navigate('/themes')}>테마</button>
              <button onClick={() => navigate('/route/auto')}>자동 추천</button>
              <button onClick={() => setIsRouteAdjustOpen((v) => !v)}>경로 조정</button>
              <button onClick={() => setIsRouteAnalysisOpen((v) => !v)}>경로 분석</button>
              {spotIds.length > 0 && (
                <button className="primary" onClick={() => navigate('/route/save')}>
                  저장 ({spotIds.length})
                </button>
              )}
            </div>
            <div className="map-toolbar__right">
              <button onClick={clear}>로그아웃</button>
            </div>
          </div>
        )}
      </div>

      {/* 팝오버는 Kakao CustomOverlay로 지도 위에 직접 표시됨 */}

      {/* 길찾기 요약 배지 */}
      {directionsInfo && orderedPoints.length >= 2 && (
        <div className="directions-badge">
          <span className="directions-badge__distance">
            🚗 {formatDistance(directionsInfo.total_distance_m)}
          </span>
          <span className="directions-badge__duration">
            ⏱ {formatDuration(directionsInfo.total_duration_sec)}
          </span>
          {directionsInfo.toll_fee > 0 && (
            <span className="directions-badge__toll">
              💰 {directionsInfo.toll_fee.toLocaleString()}원
            </span>
          )}
        </div>
      )}
      {directionsLoading && orderedPoints.length >= 2 && (
        <div className="directions-badge loading">경로 계산 중...</div>
      )}

      {isRouteAdjustOpen && (
        <RouteAdjustPanel
          points={orderedPoints}
          onReorder={setOrderedPoints}
          onClose={() => setIsRouteAdjustOpen(false)}
        />
      )}
      {isRouteAnalysisOpen && (
        <RouteAnalysisPanel
          points={orderedPoints}
          directionsInfo={directionsInfo}
          directionsLoading={directionsLoading}
          onClose={() => setIsRouteAnalysisOpen(false)}
        />
      )}
    </div>
  );
}

interface MenuRowProps {
  isCompact: boolean;
  map: any;
  userEmail: string | null;
  userNickname: string | null;
  routeGroups: RouteGroup[];
  activeRouteId: string;
  spotCount: number;
  onSwitchGroup: (id: string) => void;
  onAddGroup: () => void;
  onTheme: () => void;
  onAuto: () => void;
  onSave: () => void;
  onLogout: () => void;
  onRouteAdjust: () => void;
  onRouteAnalysis: () => void;
}

function MenuRow({
  isCompact, map, userEmail, userNickname,
  routeGroups, activeRouteId, spotCount,
  onSwitchGroup, onAddGroup,
  onTheme, onAuto, onSave, onLogout, onRouteAdjust, onRouteAnalysis,
}: MenuRowProps) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isDrawerClosing, setIsDrawerClosing] = useState(false);
  const [drawerStyle, setDrawerStyle] = useState<CSSProperties>({});
  const drawerCloseTimerRef = useRef<number | null>(null);

  const syncDrawerPosition = () => {
    const header = document.querySelector('.map-header');
    const headerBottom = header?.getBoundingClientRect().bottom ?? 0;
    setDrawerStyle({
      '--drawer-top': `${Math.round(headerBottom + DRAWER_EDGE_GAP_PX)}px`,
      '--drawer-gap': `${DRAWER_EDGE_GAP_PX}px`,
    } as CSSProperties);
  };

  const clearDrawerTimer = () => {
    if (drawerCloseTimerRef.current !== null) {
      window.clearTimeout(drawerCloseTimerRef.current);
      drawerCloseTimerRef.current = null;
    }
  };

  const openDrawer = () => {
    clearDrawerTimer();
    syncDrawerPosition();
    setIsDrawerClosing(false);
    setIsDrawerOpen(true);
  };

  const closeDrawer = () => {
    if (!isDrawerOpen) return;
    clearDrawerTimer();
    setIsDrawerClosing(true);
    setIsDrawerOpen(false);
    drawerCloseTimerRef.current = window.setTimeout(() => {
      setIsDrawerClosing(false);
      drawerCloseTimerRef.current = null;
    }, DRAWER_ANIMATION_MS);
  };

  useEffect(() => {
    closeDrawer();
    const closeOnResize = () => {
      syncDrawerPosition();
      closeDrawer();
    };
    window.addEventListener('resize', closeOnResize);
    return () => {
      window.removeEventListener('resize', closeOnResize);
      clearDrawerTimer();
    };
  }, [isCompact]);

  const display = userNickname || userEmail || '?';
  const initial = display.trim().charAt(0).toUpperCase() || '?';

  const routeSelect = (
    <div className="map-header__route-select">
      <select
        value={activeRouteId}
        onChange={(e) => onSwitchGroup(e.target.value)}
      >
        {routeGroups.map((g) => (
          <option key={g.id} value={g.id}>{g.name}</option>
        ))}
      </select>
      <button type="button" className="route-add-btn" onClick={onAddGroup}>+</button>
    </div>
  );

  const drawer =
    isCompact && (isDrawerOpen || isDrawerClosing) && typeof document !== 'undefined'
      ? createPortal(
          <>
            <div className="side-drawer-backdrop open" onClick={closeDrawer} />
            <aside className={`side-drawer ${isDrawerClosing ? 'closing' : 'open'}`} style={drawerStyle}>
              <div className="side-drawer__header">
                <strong>메뉴</strong>
                <button type="button" onClick={closeDrawer} aria-label="메뉴 닫기">
                  &times;
                </button>
              </div>
              {routeSelect}
              <button onClick={() => { closeDrawer(); onTheme(); }}>테마 선택</button>
              <button onClick={() => { closeDrawer(); onAuto(); }}>자동 추천</button>
              <button onClick={() => { closeDrawer(); onRouteAdjust(); }}>경로 조정</button>
              <button onClick={() => { closeDrawer(); onRouteAnalysis(); }}>경로 분석</button>
              {spotCount > 0 && (
                <button onClick={() => { closeDrawer(); onSave(); }}>
                  루트 저장 ({spotCount})
                </button>
              )}
              <button className="danger" onClick={() => { closeDrawer(); onLogout(); }}>
                로그아웃
              </button>
            </aside>
          </>,
          document.body
        )
      : null;

  const profileBlock = (
    <div className="profile-block map-header__profile">
      <div className="profile-info">
        <strong>{userNickname || '닉네임 미설정'}</strong>
        <small>{userEmail ?? ''}</small>
      </div>
      <button
        type="button"
        className="profile-avatar"
        title="마이페이지"
        aria-label="마이페이지"
        onClick={() => alert('마이페이지는 곧 제공됩니다.')}
      >
        {initial}
      </button>
    </div>
  );

  return (
    <div className={`map-header__row ${isCompact ? 'is-compact' : 'is-expanded'}`}>
      <button
        type="button"
        className="mobile-menu-button"
        aria-label="메뉴 열기"
        onClick={openDrawer}
      >
        <span />
        <span />
        <span />
      </button>
      <div className="map-header__brand">
        <span className="map-header__title">Pilgrimage</span>
        {!isCompact && profileBlock}
      </div>
      {!isCompact && routeSelect}
      {isCompact && <SearchBar map={map} className="map-search--inline" />}
      {isCompact && profileBlock}
      {drawer}
    </div>
  );
}

interface SearchBarProps {
  map: any;
  className?: string;
}

function SearchBar({ map, className = '' }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [error, setError] = useState<string | null>(null);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!map || !query.trim()) return;
    const services = window.kakao?.maps?.services;
    if (!services) {
      setError('검색 모듈을 불러오지 못했어요');
      return;
    }
    const geocoder = new services.Geocoder();
    geocoder.addressSearch(query.trim(), (result: any[], status: string) => {
      if (status === services.Status.OK && result.length > 0) {
        const { x, y } = result[0];
        map.setCenter(new window.kakao.maps.LatLng(parseFloat(y), parseFloat(x)));
        map.setLevel(4);
      } else {
        setError('해당 주소를 찾지 못했어요');
      }
    });
  };

  return (
    <form className={`map-search ${className}`} onSubmit={onSubmit}>
      <input
        type="text"
        placeholder="주소를 입력하세요 (예: 서울 종로구 사직로 161)"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button type="submit">검색</button>
      {error && <span className="search-error">{error}</span>}
    </form>
  );
}

function AuthInline() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === 'register') {
        await register({ email, password, nickname });
      }
      const resp = await login(email, password);
      setTokens(resp.access, resp.refresh, resp.email || email, resp.nickname);
    } catch (err) {
      setError(err instanceof Error ? err.message : '인증 실패');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="map-header__brand">
        <span className="map-header__title">Pilgrimage</span>
        <p className="map-header__tag">맞춤 여행 경로 + GPS 30분 인증</p>
      </div>

      <form onSubmit={onSubmit} className="auth-form">
        <input
          type="email" placeholder="이메일"
          value={email} onChange={(e) => setEmail(e.target.value)}
          required autoFocus
        />
        <input
          type="password" placeholder="비밀번호 (8자 이상)"
          value={password} onChange={(e) => setPassword(e.target.value)}
          required minLength={8}
        />
        {mode === 'register' && (
          <input
            type="text" placeholder="닉네임"
            value={nickname} onChange={(e) => setNickname(e.target.value)}
          />
        )}
        <button type="submit" disabled={submitting}>
          {submitting
            ? '처리 중...'
            : mode === 'register' ? '회원가입' : '로그인'}
        </button>
        {error && <div className="auth-error">{error}</div>}
        <button
          type="button"
          className="auth-link"
          onClick={() => setMode((m) => (m === 'register' ? 'login' : 'register'))}
        >
          {mode === 'register' ? '이미 회원이신가요? 로그인' : '회원가입'}
        </button>
      </form>
    </>
  );
}

interface RouteAdjustPanelProps {
  points: OrderedPoint[];
  onReorder: (next: OrderedPoint[]) => void;
  onClose: () => void;
}

const TRANSPORT_MODES = [
  { key: 'walk',    label: '도보',     icon: '🚶' },
  { key: 'bike',    label: '자전거',   icon: '🚲' },
  { key: 'car',     label: '자동차',   icon: '🚗' },
  { key: 'transit', label: '대중교통', icon: '🚌' },
] as const;

type TransportKey = typeof TRANSPORT_MODES[number]['key'];

interface RouteAnalysisPanelProps {
  points: OrderedPoint[];
  directionsInfo: DirectionsResult | null;
  directionsLoading: boolean;
  onClose: () => void;
}

function RouteAnalysisPanel({ points, directionsInfo, directionsLoading, onClose }: RouteAnalysisPanelProps) {
  const [segmentModes, setSegmentModes] = useState<Record<number, TransportKey>>({});

  const segments = points.length >= 2
    ? points.slice(0, -1).map((p, i) => ({ from: p, to: points[i + 1], index: i }))
    : [];

  const allSelected = segments.length > 0 && segments.every((s) => segmentModes[s.index] !== undefined);
  const remaining = segments.filter((s) => segmentModes[s.index] === undefined).length;

  return (
    <div className="route-analysis-panel">
      <div className="route-analysis-panel__header">
        <strong>경로 분석</strong>
        <button type="button" className="route-analysis-panel__close" onClick={onClose}>&times;</button>
      </div>

      {/* Directions summary */}
      {directionsLoading && (
        <div className="route-analysis-panel__summary loading">경로 계산 중...</div>
      )}
      {directionsInfo && !directionsLoading && (
        <div className="route-analysis-panel__summary">
          <div className="route-analysis-panel__summary-row">
            <span className="route-analysis-panel__summary-label">총 거리</span>
            <strong>{formatDistance(directionsInfo.total_distance_m)}</strong>
          </div>
          <div className="route-analysis-panel__summary-row">
            <span className="route-analysis-panel__summary-label">예상 시간</span>
            <strong>{formatDuration(directionsInfo.total_duration_sec)}</strong>
          </div>
          {directionsInfo.toll_fee > 0 && (
            <div className="route-analysis-panel__summary-row">
              <span className="route-analysis-panel__summary-label">통행료</span>
              <strong>{directionsInfo.toll_fee.toLocaleString()}원</strong>
            </div>
          )}
          {directionsInfo.sections.length > 1 && (
            <div className="route-analysis-panel__sections">
              {directionsInfo.sections.map((sec, i) => (
                <div key={i} className="route-analysis-panel__section-row">
                  <span>구간 {i + 1}</span>
                  <span>{formatDistance(sec.distance_m)}</span>
                  <span>{formatDuration(sec.duration_sec)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {!directionsInfo && !directionsLoading && segments.length >= 1 && (
        <div className="route-analysis-panel__summary muted">
          도로 경로를 가져올 수 없어 직선 거리를 표시합니다
        </div>
      )}

      {segments.length === 0 ? (
        <p className="route-analysis-panel__empty">지점을 2개 이상 설정하세요</p>
      ) : (
        <>
          <ul className="route-analysis-panel__list">
            {segments.map((seg) => (
              <li key={seg.index} className="route-analysis-panel__segment">
                <div className="route-analysis-panel__segment-label">
                  <span className="route-analysis-panel__segment-index">{seg.index + 1}</span>
                  <span className="route-analysis-panel__segment-names">
                    <span>{seg.from.name}</span>
                    <span className="route-analysis-panel__arrow">→</span>
                    <span>{seg.to.name}</span>
                  </span>
                </div>
                <div className="route-analysis-panel__modes">
                  {TRANSPORT_MODES.map((mode) => (
                    <button
                      key={mode.key}
                      type="button"
                      className={`route-analysis-panel__mode-btn${segmentModes[seg.index] === mode.key ? ' selected' : ''}`}
                      onClick={() => setSegmentModes((prev) => ({ ...prev, [seg.index]: mode.key }))}
                      title={mode.label}
                    >
                      <span>{mode.icon}</span>
                      <span>{mode.label}</span>
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
          <div className="route-analysis-panel__footer">
            <button
              type="button"
              className={`route-analysis-panel__analyze-btn${allSelected ? ' active' : ''}`}
              disabled={!allSelected}
            >
              {allSelected ? '분석 시작' : `${remaining}개 구간 선택 필요`}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function RouteAdjustPanel({ points, onReorder, onClose }: RouteAdjustPanelProps) {
  const dragIndexRef = useRef<number | null>(null);

  const handleDragStart = (index: number) => {
    dragIndexRef.current = index;
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    const from = dragIndexRef.current;
    if (from === null || from === index) return;
    const next = [...points];
    const [item] = next.splice(from, 1);
    next.splice(index, 0, item);
    dragIndexRef.current = index;
    onReorder(next);
  };

  const handleDragEnd = () => {
    dragIndexRef.current = null;
  };

  return (
    <div className="route-adjust-panel">
      <div className="route-adjust-panel__header">
        <strong>경로 조정</strong>
        <button type="button" className="route-adjust-panel__close" onClick={onClose}>&times;</button>
      </div>
      {points.length === 0 ? (
        <p className="route-adjust-panel__empty">지점을 먼저 설정하세요</p>
      ) : (
        <ol className="route-adjust-panel__list">
          {points.map((p, i) => (
            <li
              key={`${p.lat},${p.lng}`}
              className="route-adjust-panel__item"
              draggable
              onDragStart={() => handleDragStart(i)}
              onDragOver={(e) => handleDragOver(e, i)}
              onDragEnd={handleDragEnd}
            >
              <span className="route-adjust-panel__order">{i + 1}</span>
              <span className="route-adjust-panel__icon">{p.icon}</span>
              <span className="route-adjust-panel__name">{p.name}</span>
              <span className="route-adjust-panel__handle">⠿</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

