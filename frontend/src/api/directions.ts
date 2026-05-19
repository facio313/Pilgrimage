import { apiClient } from './client';

export interface LatLng {
  lat: number;
  lng: number;
}

export interface DirectionsSection {
  distance_m: number;
  duration_sec: number;
}

export interface DirectionsResult {
  polyline: LatLng[];
  total_distance_m: number;
  total_duration_sec: number;
  toll_fee: number;
  taxi_fee: number;
  sections: DirectionsSection[];
  origin: LatLng;
  destination: LatLng;
}

export type DirectionsPriority = 'RECOMMEND' | 'DISTANCE' | 'TIME';

/**
 * Fetch driving directions between two or more points.
 *
 * Coordinates use Kakao convention: lng,lat.
 * If waypoints are provided (max 5), they are visited in order.
 */
export async function getDirections(
  origin: LatLng,
  destination: LatLng,
  waypoints?: LatLng[],
  priority: DirectionsPriority = 'RECOMMEND',
): Promise<DirectionsResult> {
  const params: Record<string, string> = {
    origin: `${origin.lng},${origin.lat}`,
    destination: `${destination.lng},${destination.lat}`,
    priority,
  };

  if (waypoints && waypoints.length > 0) {
    params.waypoints = waypoints.map((w) => `${w.lng},${w.lat}`).join('|');
  }

  const res = await apiClient.get<DirectionsResult>('/directions/', { params });
  return res.data;
}

/** Format meters into human-readable distance. */
export function formatDistance(meters: number): string {
  if (meters < 1000) return `${meters}m`;
  return `${(meters / 1000).toFixed(1)}km`;
}

/** Format seconds into human-readable duration. */
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours}시간 ${minutes}분`;
  return `${minutes}분`;
}
