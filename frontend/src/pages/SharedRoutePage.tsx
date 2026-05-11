import { useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getSharedRoute } from '../api/routes';
import { useKakaoMap } from '../hooks/useKakaoMap';

const SEOUL_CITY_HALL = { lat: 37.5666103, lng: 126.9783882 };

export function SharedRoutePage() {
  const { token = '' } = useParams<{ token: string }>();
  const { containerRef, map, error } = useKakaoMap({ center: SEOUL_CITY_HALL });

  const { data: route, isLoading, error: queryError } = useQuery({
    queryKey: ['shared-route', token],
    queryFn: () => getSharedRoute(token),
    enabled: !!token,
  });

  const layersRef = useRef<any[]>([]);
  useEffect(() => {
    if (!map || !route) return;
    layersRef.current.forEach((l) => l.setMap(null));
    layersRef.current = [];
    const kakao = window.kakao;
    const points = [...route.route_spots]
      .sort((a, b) => a.sequence_order - b.sequence_order)
      .map((rs) => ({ lat: rs.spot.lat, lng: rs.spot.lng, name: rs.spot.name }));

    const bounds = new kakao.maps.LatLngBounds();
    points.forEach((p, idx) => {
      const pos = new kakao.maps.LatLng(p.lat, p.lng);
      const marker = new kakao.maps.Marker({ map, position: pos, title: `${idx + 1}. ${p.name}` });
      layersRef.current.push(marker);
      bounds.extend(pos);
    });

    if (points.length >= 2) {
      const polyline = new kakao.maps.Polyline({
        map,
        path: points.map((p) => new kakao.maps.LatLng(p.lat, p.lng)),
        strokeWeight: 4,
        strokeColor: '#1a73e8',
        strokeOpacity: 0.8,
      });
      layersRef.current.push(polyline);
    }
    if (points.length > 0) map.setBounds(bounds);

    return () => {
      layersRef.current.forEach((l) => l.setMap(null));
      layersRef.current = [];
    };
  }, [map, route]);

  if (error) return <div style={{ padding: 16, color: '#c00' }}>지도 로딩 실패: {error.message}</div>;
  if (queryError) return <div style={{ padding: 16, color: '#c00' }}>경로를 찾을 수 없습니다.</div>;

  return (
    <div style={{ position: 'relative', height: '100vh' }}>
      <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
      <header style={overlayStyle}>
        {isLoading && <span>로딩 중...</span>}
        {route && (
          <div>
            <strong>{route.title}</strong>
            <div style={{ fontSize: 13, color: '#555' }}>
              총 거리 {route.total_distance_km} km · 예상 비용 {route.total_estimated_cost.toLocaleString()}원 · 장소 {route.route_spots.length}개
            </div>
          </div>
        )}
      </header>
    </div>
  );
}

const overlayStyle: React.CSSProperties = {
  position: 'absolute',
  top: 12,
  left: 12,
  right: 12,
  padding: '10px 14px',
  background: 'rgba(255,255,255,0.95)',
  borderRadius: 8,
  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  zIndex: 10,
};
