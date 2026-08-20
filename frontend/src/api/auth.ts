import { apiClient } from './client';

export interface LoginResponse {
  access: string;
  refresh: string;
  email: string;
  nickname: string;
}

export async function register(payload: {
  email: string;
  password: string;
  nickname?: string;
}) {
  const res = await apiClient.post('/auth/register/', payload);
  return res.data;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await apiClient.post<LoginResponse>('/auth/login/', {
    username: email,
    password,
  });
  return res.data;
}

export async function exchangeSso(): Promise<LoginResponse> {
  const res = await apiClient.post<LoginResponse>('/auth/sso/');
  return res.data;
}
