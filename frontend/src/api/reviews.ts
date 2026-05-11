import { apiClient } from './client';

export interface Review {
  id: string;
  spot: string;
  user: string;
  user_nickname: string;
  rating: number;
  body: string;
  entrance_fee: number;
  food_cost: number;
  other_cost: number;
  photo_paths: string[];
  created_at: string;
}

export interface CreateReviewPayload {
  visit_log_id: string;
  rating: number;
  body?: string;
  entrance_fee?: number;
  food_cost?: number;
  other_cost?: number;
  photo_paths?: string[];
}

interface PaginatedResponse<T> {
  count: number;
  results: T[];
}

export async function listReviews(spotId: string): Promise<Review[]> {
  const res = await apiClient.get<PaginatedResponse<Review> | Review[]>('/reviews/', {
    params: { spot_id: spotId },
  });
  return Array.isArray(res.data) ? res.data : res.data.results;
}

export async function createReview(payload: CreateReviewPayload): Promise<Review> {
  const res = await apiClient.post<Review>('/reviews/', payload);
  return res.data;
}
