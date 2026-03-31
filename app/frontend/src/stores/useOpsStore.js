import { create } from 'zustand';

export const useOpsStore = create((set) => ({
  ssid: '',
  sessionId: null,
  chromeStatus: 'stopped', // 'running' | 'stopped' | 'busy'
  sessionStatus: 'disconnected', // 'connected' | 'disconnected' | 'busy'
  balance: 0,
  accountType: null, // 'demo' | 'real'
  error: null,

  setSsid: (ssid) => set({ ssid }),
  setSessionId: (sessionId) => set({ sessionId }),
  setChromeStatus: (status) => set({ chromeStatus: status }),
  setSessionStatus: (status) => set({ sessionStatus: status }),
  setBalance: (balance) => set({ balance }),
  setAccountType: (type) => set({ accountType: type }),
  setError: (error) => set({ error }),
}));
