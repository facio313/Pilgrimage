import { useEffect, useRef, useState } from 'react';
import { loadKakao } from '../lib/kakaoLoader';

interface UseKakaoMapOptions {
  center: { lat: number; lng: number };
  level?: number;
}

export function useKakaoMap({ center, level = 5 }: UseKakaoMapOptions) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [map, setMap] = useState<any>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadKakao()
      .then((kakao) => {
        if (cancelled || !containerRef.current) return;
        const instance = new kakao.maps.Map(containerRef.current, {
          center: new kakao.maps.LatLng(center.lat, center.lng),
          level,
        });
        instance.setCursor('default');
        setMap(instance);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { containerRef, map, error };
}
