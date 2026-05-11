import { create } from 'zustand';

export type TransportMode = 'car' | 'bus' | 'train' | 'walking' | 'bicycle' | 'mixed';

interface RouteDraftState {
  theme: string | null;
  spotIds: string[];
  transportMode: TransportMode;
  setTheme: (theme: string) => void;
  addSpot: (id: string) => void;
  removeSpot: (id: string) => void;
  reorder: (ids: string[]) => void;
  setTransport: (mode: TransportMode) => void;
  reset: () => void;
}

export const useRouteDraftStore = create<RouteDraftState>((set) => ({
  theme: null,
  spotIds: [],
  transportMode: 'mixed',
  setTheme: (theme) => set({ theme }),
  addSpot: (id) =>
    set((s) => (s.spotIds.includes(id) ? s : { spotIds: [...s.spotIds, id] })),
  removeSpot: (id) => set((s) => ({ spotIds: s.spotIds.filter((x) => x !== id) })),
  reorder: (ids) => set({ spotIds: ids }),
  setTransport: (mode) => set({ transportMode: mode }),
  reset: () => set({ theme: null, spotIds: [], transportMode: 'mixed' }),
}));
