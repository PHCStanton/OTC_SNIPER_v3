import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useNotificationStore = create()(
  persist(
    (set) => ({
      notifications: [],

      addNotification: ({ type = 'info', message, timestamp }) => {
        const id = Date.now().toString(36) + Math.random().toString(36).substring(2, 7);
        set((state) => {
          const newNotif = {
            id,
            type,
            message,
            timestamp: timestamp || Date.now() / 1000,
            unread: true,
          };
          return {
            notifications: [newNotif, ...state.notifications].slice(0, 50),
          };
        });
      },

      markAsRead: (id) =>
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, unread: false } : n
          ),
        })),

      markAllAsRead: () =>
        set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, unread: false })),
        })),

      clearAll: () => set({ notifications: [] }),
    }),
    {
      name: 'otc-sniper-notification-storage',
    }
  )
);
