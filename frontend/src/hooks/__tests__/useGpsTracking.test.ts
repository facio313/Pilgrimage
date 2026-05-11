import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useGpsTracking } from '../useGpsTracking';

vi.mock('../../api/visits', () => ({
  postGpsLog: vi.fn().mockResolvedValue(undefined),
}));

import { postGpsLog } from '../../api/visits';

const mockedPostGpsLog = vi.mocked(postGpsLog);

function fakePosition(lat: number, lng: number) {
  return {
    coords: {
      latitude: lat,
      longitude: lng,
      accuracy: 10,
      altitude: null,
      altitudeAccuracy: null,
      heading: null,
      speed: null,
    },
    timestamp: Date.now(),
  } as GeolocationPosition;
}

describe('useGpsTracking', () => {
  beforeEach(() => {
    mockedPostGpsLog.mockClear();
    Object.defineProperty(window, 'isSecureContext', { value: true, configurable: true });
    Object.defineProperty(navigator, 'geolocation', {
      value: {
        getCurrentPosition: vi.fn((success: PositionCallback) => {
          success(fakePosition(37.5, 127.0));
        }),
        watchPosition: vi.fn(),
        clearWatch: vi.fn(),
      },
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does not start tracking when active is false', () => {
    const { result } = renderHook(() => useGpsTracking(false));
    expect(result.current.active).toBe(false);
    expect(mockedPostGpsLog).not.toHaveBeenCalled();
  });

  it('reports an error when not in a secure context', async () => {
    Object.defineProperty(window, 'isSecureContext', { value: false, configurable: true });
    const { result } = renderHook(() => useGpsTracking(true));
    await waitFor(() => {
      expect(result.current.error).toMatch(/HTTPS/);
    });
  });

  it('sends a GPS log immediately when activated', async () => {
    renderHook(() => useGpsTracking(true));
    await waitFor(() => {
      expect(mockedPostGpsLog).toHaveBeenCalledTimes(1);
    });
    expect(mockedPostGpsLog).toHaveBeenCalledWith(
      expect.objectContaining({ lat: 37.5, lng: 127.0 })
    );
  });

  it('reports geolocation errors from the browser', async () => {
    Object.defineProperty(navigator, 'geolocation', {
      value: {
        getCurrentPosition: vi.fn(
          (_success: PositionCallback, error?: PositionErrorCallback) => {
            error?.({
              code: 1,
              message: 'Permission denied',
              PERMISSION_DENIED: 1,
              POSITION_UNAVAILABLE: 2,
              TIMEOUT: 3,
            } as GeolocationPositionError);
          }
        ),
        watchPosition: vi.fn(),
        clearWatch: vi.fn(),
      },
      configurable: true,
    });
    const { result } = renderHook(() => useGpsTracking(true));
    await waitFor(() => {
      expect(result.current.error).toBe('Permission denied');
    });
  });
});
