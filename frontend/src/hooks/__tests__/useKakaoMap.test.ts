import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useKakaoMap } from '../useKakaoMap';

vi.mock('../../lib/kakaoLoader', () => ({
  loadKakao: vi.fn(),
}));

import { loadKakao } from '../../lib/kakaoLoader';

const mockedLoadKakao = vi.mocked(loadKakao);

describe('useKakaoMap', () => {
  beforeEach(() => {
    mockedLoadKakao.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns a containerRef and a null map before the SDK resolves', () => {
    mockedLoadKakao.mockReturnValueOnce(new Promise(() => {}));
    const { result } = renderHook(() =>
      useKakaoMap({ center: { lat: 37.5, lng: 127.0 } })
    );
    expect(result.current.containerRef).toBeDefined();
    expect(result.current.map).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('captures load errors into the error state', async () => {
    mockedLoadKakao.mockRejectedValueOnce(new Error('SDK load failed'));
    const { result } = renderHook(() =>
      useKakaoMap({ center: { lat: 37.5, lng: 127.0 } })
    );
    await waitFor(() => {
      expect(result.current.error).toBeInstanceOf(Error);
      expect(result.current.error?.message).toBe('SDK load failed');
    });
    expect(result.current.map).toBeNull();
  });

  it('does not create a Map instance when no container is mounted', async () => {
    const mapCtor = vi.fn();
    mockedLoadKakao.mockResolvedValueOnce({
      maps: { Map: mapCtor, LatLng: vi.fn() },
    });
    const { result } = renderHook(() =>
      useKakaoMap({ center: { lat: 37.5, lng: 127.0 } })
    );
    // Without a real container the hook returns early; map remains null.
    await waitFor(() => {
      expect(mockedLoadKakao).toHaveBeenCalled();
    });
    expect(mapCtor).not.toHaveBeenCalled();
    expect(result.current.map).toBeNull();
  });
});
