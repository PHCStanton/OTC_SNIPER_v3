/**
 * Toast notification store — lightweight, self-expiring toast queue.
 * Supports: success | error | warning | info
 * Usage: useToastStore.getState().addToast({ type: 'success', message: 'Trade executed.' })
 */
import { create } from 'zustand';

let _nextId = 1;

export const useToastStore = create((set) => ({
  toasts: [],

  /**
   * Add a toast. Auto-removes after `duration` ms (default 4000).
   * @param {{ type: 'success'|'error'|'warning'|'info', message: string, duration?: number }} toast
   */
  addToast: ({ type = 'info', message, duration = 4000 }) => {
    const id = _nextId++;
    set((state) => ({ toasts: [...state.toasts, { id, type, message }] }));

    if (duration > 0) {
      setTimeout(() => {
        set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
      }, duration);
    }
  },

  removeToast: (id) =>
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),

  clearToasts: () => set({ toasts: [] }),
}));
