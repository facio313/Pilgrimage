import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  userEmail: string | null;
  userNickname: string | null;
  setTokens: (access: string, refresh: string, email?: string, nickname?: string) => void;
  setAccessToken: (access: string) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      userEmail: null,
      userNickname: null,
      setTokens: (access, refresh, email, nickname) =>
        set({
          accessToken: access,
          refreshToken: refresh,
          userEmail: email ?? null,
          userNickname: nickname ?? null,
        }),
      setAccessToken: (access) => set({ accessToken: access }),
      clear: () =>
        set({
          accessToken: null,
          refreshToken: null,
          userEmail: null,
          userNickname: null,
        }),
    }),
    { name: 'pilgrimage-auth' }
  )
);
