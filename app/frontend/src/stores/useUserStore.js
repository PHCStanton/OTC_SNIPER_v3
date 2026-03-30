/**
 * Reserved user/profile store for future Auth0 integration.
 * Keep SSID session control separate in useAuthStore.
 */
import { create } from 'zustand';

export const useUserStore = create((set) => ({
  profile: null,
  profileLoaded: false,

  setProfile: (profile) => set({ profile }),
  clearProfile: () => set({ profile: null }),
  setProfileLoaded: (profileLoaded) => set({ profileLoaded }),
}));