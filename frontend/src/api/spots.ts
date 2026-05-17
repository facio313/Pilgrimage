import { apiClient } from './client';

export interface Spot {
  id: string;
  external_id: string;
  name: string;
  category: string;
  theme_tags: string[];
  lat: number;
  lng: number;
  address: string;
  avg_review_score: string;
}

export interface SpotDetail extends Spot {
  operating_hours: Record<string, unknown>;
  entrance_fee: number;
  avg_cost: number;
  avg_stay_minutes: number;
  synced_at: string | null;
}

export interface SpotListParams {
  theme?: string;
  lat?: number;
  lng?: number;
  radius?: number;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export async function listSpots(params: SpotListParams = {}): Promise<Spot[]> {
  const res = await apiClient.get<PaginatedResponse<Spot> | Spot[]>('/spots/', { params });
  return Array.isArray(res.data) ? res.data : res.data.results;
}

export async function getSpot(id: string): Promise<SpotDetail> {
  const res = await apiClient.get<SpotDetail>(`/spots/${id}/`);
  return res.data;
}

export interface NearbySpot extends Spot {
  bearing: number;
  distance_m: number;
}

export async function upsertSpot(input: {
  name: string;
  lat: number;
  lng: number;
  address?: string;
  category?: string;
  external_id?: string;
}): Promise<Spot> {
  const res = await apiClient.post<Spot>('/spots/', input);
  return res.data;
}

export async function getNearbyRecommend(params: {
  lat: number;
  lng: number;
  theme?: string;
}): Promise<NearbySpot[]> {
  const res = await apiClient.get<NearbySpot[]>('/spots/nearby-recommend/', {
    params,
  });
  return res.data;
}
