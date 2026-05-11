import { apiClient } from './client';

export type VisitStatus = 'UNVISITED' | 'CERTIFIED' | 'REJECTED';

export interface VisitLog {
  id: string;
  spot: string;
  status: VisitStatus;
  stay_start_at: string | null;
  stay_end_at: string | null;
  stay_minutes: number;
  certified_at: string | null;
}

export interface GpsLogPayload {
  lat: number;
  lng: number;
  recorded_at: string;
}

export async function postGpsLog(payload: GpsLogPayload): Promise<void> {
  await apiClient.post('/gps/log/', payload);
}

export async function certifyVisit(spotId: string): Promise<VisitLog> {
  const res = await apiClient.post<VisitLog>(`/visits/${spotId}/certify/`);
  return res.data;
}
