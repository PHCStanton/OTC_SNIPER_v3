/**
 * Auth store — SSID input state and connect/disconnect actions.
 * Wraps opsApi calls and syncs result into useOpsStore.
 */
import { create } from 'zustand';
import { sessionConnect, sessionDisconnect } from '../api/opsApi.js';
import { useOpsStore } from './useOpsStore.js';
import { useToastStore } from './useToastStore.js';

export const useAuthStore = create((set) => ({
  ssidInput: '',
  isDemo: true,
  isConnecting: false,
  isDisconnecting: false,
  connectError: null,

  setSsidInput: (val) => set({ ssidInput: val }),
  setIsDemo: (val) => set({ isDemo: val }),

  connect: async (ssid, demo) => {
    set({ isConnecting: true, connectError: null });
    try {
      const data = await sessionConnect(ssid ?? '', demo);
      const ops = useOpsStore.getState();
      ops.setSessionStatus('connected');
      if (data.balance != null) ops.setBalance(data.balance);
      if (data.account_type != null) ops.setAccountType(data.account_type);
      set({ ssidInput: '', connectError: null });
      const accountLabel = (data.account_type ?? (demo ? 'demo' : 'real')).toUpperCase();
      useToastStore.getState().addToast({ type: 'success', message: `Session connected — ${accountLabel} account` });
    } catch (err) {
      set({ connectError: err.message });
      useToastStore.getState().addToast({ type: 'error', message: `Connection failed: ${err.message}` });
    } finally {
      set({ isConnecting: false });
    }
  },

  disconnect: async () => {
    set({ isDisconnecting: true, connectError: null });
    try {
      await sessionDisconnect();
      const ops = useOpsStore.getState();
      ops.setSessionStatus('disconnected');
      ops.setBalance(0);
      ops.setAccountType(null);
      useToastStore.getState().addToast({ type: 'info', message: 'Session disconnected.' });
    } catch (err) {
      set({ connectError: err.message });
      useToastStore.getState().addToast({ type: 'error', message: `Disconnect failed: ${err.message}` });
    } finally {
      set({ isDisconnecting: false });
    }
  },
}));
