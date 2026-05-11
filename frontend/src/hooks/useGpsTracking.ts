import { useEffect, useRef, useState } from 'react';
import { postGpsLog } from '../api/visits';

const GPS_LOG_INTERVAL_MS = 30_000;

export interface GpsTrackingState {
  active: boolean;
  paused: boolean;
  lastPosition: { lat: number; lng: number; recordedAt: string } | null;
  error: string | null;
}

export function useGpsTracking(active: boolean) {
  const [state, setState] = useState<GpsTrackingState>({
    active: false,
    paused: false,
    lastPosition: null,
    error: null,
  });
  const intervalRef = useRef<number | null>(null);
  const pausedRef = useRef(false);

  useEffect(() => {
    if (!active) {
      setState((s) => ({ ...s, active: false }));
      return;
    }

    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setState((s) => ({ ...s, error: 'Geolocation API not available' }));
      return;
    }

    if (!window.isSecureContext) {
      setState((s) => ({ ...s, error: 'GPS requires HTTPS (secure context)' }));
      return;
    }

    setState((s) => ({ ...s, active: true, error: null }));

    const sendOnce = () => {
      if (pausedRef.current) return;
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          const recordedAt = new Date(pos.timestamp).toISOString();
          const payload = {
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
            recorded_at: recordedAt,
          };
          try {
            await postGpsLog(payload);
            setState((s) => ({
              ...s,
              lastPosition: { lat: payload.lat, lng: payload.lng, recordedAt },
              error: null,
            }));
          } catch (err) {
            setState((s) => ({
              ...s,
              error: err instanceof Error ? err.message : 'GPS log failed',
            }));
          }
        },
        (err) => {
          setState((s) => ({ ...s, error: err.message }));
        },
        { enableHighAccuracy: true, timeout: 10_000, maximumAge: 0 }
      );
    };

    sendOnce();
    intervalRef.current = window.setInterval(sendOnce, GPS_LOG_INTERVAL_MS);

    const handleVisibility = () => {
      const hidden = document.visibilityState === 'hidden';
      pausedRef.current = hidden;
      setState((s) => ({ ...s, paused: hidden }));
    };

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };

    document.addEventListener('visibilitychange', handleVisibility);
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      document.removeEventListener('visibilitychange', handleVisibility);
      window.removeEventListener('beforeunload', handleBeforeUnload);
      pausedRef.current = false;
      setState({ active: false, paused: false, lastPosition: null, error: null });
    };
  }, [active]);

  return state;
}
