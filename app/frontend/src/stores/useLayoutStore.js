import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useLayoutStore = create()(
  persist(
    (set) => ({
      sidebarOpen: true,
      activeView: 'trading', // 'trading' | 'risk' | 'journal' | 'settings'
      dashboardMode: 'trading', // 'trading' | 'risk' (for the dashboard toggle)

      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setActiveView: (view) => set({ activeView: view }),
      setDashboardMode: (mode) => set({ dashboardMode: mode }),
    }),
    {
      name: 'otc-sniper-layout-storage',
    }
  )
);
