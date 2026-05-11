import { apiClient } from './client';
import type { Spot } from './spots';
import type { TransportMode } from '../store/route';

export interface RouteSpotEntry {
  spot: Spot;
  sequence_order: number;
  segment_distance_km: string;
  segment_cost: number;
  segment_duration_minutes: number;
}

export interface Route {
  id: string;
  creator: string;
  title: string;
  theme_tags: string[];
  transport_mode: string;
  total_distance_km: string;
  total_estimated_cost: number;
  is_public: boolean;
  fork_from: string | null;
  created_at: string;
  updated_at: string;
  route_spots: RouteSpotEntry[];
}

export interface CreateRoutePayload {
  title: string;
  theme_tags: string[];
  transport_mode: TransportMode;
  is_public: boolean;
  spot_ids: string[];
}

export interface AutoRoutePayload {
  theme: string;
  n_spots: number;
  budget_max: number;
  min_rating: number;
  max_distance_km: number;
  transport_mode: TransportMode;
}

export async function createRoute(payload: CreateRoutePayload): Promise<Route> {
  const res = await apiClient.post<Route>('/routes/', payload);
  return res.data;
}

export async function getRoute(id: string): Promise<Route> {
  const res = await apiClient.get<Route>(`/routes/${id}/`);
  return res.data;
}

export async function autoRecommendRoute(payload: AutoRoutePayload): Promise<Route> {
  const res = await apiClient.post<Route>('/routes/auto/', payload);
  return res.data;
}

export async function shareRoute(id: string): Promise<{ share_token: string }> {
  const res = await apiClient.post<{ share_token: string }>(`/routes/${id}/share/`);
  return res.data;
}

export async function forkRoute(id: string): Promise<Route> {
  const res = await apiClient.post<Route>(`/routes/${id}/fork/`);
  return res.data;
}

export async function getSharedRoute(token: string): Promise<Route> {
  const res = await apiClient.get<Route>(`/shared/${token}/`);
  return res.data;
}
