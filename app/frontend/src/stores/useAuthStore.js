/**
 * Auth store — SSID input state and connect/disconnect actions.
 * Wraps opsApi calls and syncs result into useOpsStore.
 */
import { create } from 'zustand';
import { getBrokerAssets } from '../api/tradingApi.js';
import { sessionConnect, sessionDisconnect, sessionSavedSsid } from '../api/opsApi.js';
import { useAssetStore } from './useAssetStore.js';
import { useOpsStore } from './useOpsStore.js';
import { useToastStore } from './useToastStore.js';

export const useAuthStore = create((set, get) => ({
  ssidInput: '',
  isDemo: true,
  isConnecting: false,
  isDisconnecting: false,
  isLoadingSavedSsid: false,
  hasSavedSsid: false,
  connectError: null,

  setSsidInput: (val) => set({ ssidInput: val }),
  setIsDemo: (val) => set({ isDemo: val }),
  loadSavedSsid: async (demo) => {
    set({ isLoadingSavedSsid: true });
    try {
      const data = await sessionSavedSsid(demo);
      const savedSsid = typeof data?.ssid === 'string' ? data.ssid : '';
      const hasSavedSsid = Boolean(data?.has_saved_ssid) && savedSsid.trim().length > 0;
      set({
        ssidInput: savedSsid,
        isDemo: demo,
        hasSavedSsid,
      });
      return hasSavedSsid;
    } catch (err) {
      set({
        ssidInput: '',
        isDemo: demo,
        hasSavedSsid: false,
      });
      return false;
    } finally {
      set({ isLoadingSavedSsid: false });
    }
  },
  hydrateSavedSsid: async () => {
    const preferredDemo = get().isDemo;
    const preferredFound = await get().loadSavedSsid(preferredDemo);
    if (preferredFound) {
      return;
    }
    await get().loadSavedSsid(!preferredDemo);
  },

  connect: async (ssid, demo) => {
    set({ isConnecting: true, connectError: null });
    try {
      const data = await sessionConnect(ssid ?? '', demo);
      const ops = useOpsStore.getState();
      ops.setSessionStatus('connected');
      ops.setSessionId(data.session_id ?? null);
      if (data.balance != null) ops.setBalance(data.balance);
      if (data.account_type != null) ops.setAccountType(data.account_type);
      set({ ssidInput: '', connectError: null, hasSavedSsid: false });
      const accountLabel = (data.account_type ?? (demo ? 'demo' : 'real')).toUpperCase();
      useToastStore.getState().addToast({ type: 'success', message: `Session connected — ${accountLabel} account` });

      try {
        const assetsData = await getBrokerAssets('pocket_option');
        const rawAssets = Array.isArray(assetsData?.assets) ? assetsData.assets : [];

        const assetIds = rawAssets
          .map((asset) => String(asset?.raw_id ?? asset?.id ?? '').trim())
          .filter((assetId) => assetId.length > 0);

        if (assetIds.length > 0) {
          const assetStore = useAssetStore.getState();
          assetStore.setAssetCatalog(rawAssets);
          if (!assetIds.includes(assetStore.selectedAsset)) {
            assetStore.setSelectedAsset(assetIds[0]);
          }
        }
      } catch (assetErr) {
        console.warn('[useAuthStore] Asset list refresh failed (non-fatal):', assetErr.message);
      }
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
      ops.setSessionId(null);
      ops.setBalance(0);
      ops.setAccountType(null);
      await get().hydrateSavedSsid();
      useToastStore.getState().addToast({ type: 'info', message: 'Session disconnected.' });
    } catch (err) {
      set({ connectError: err.message });
      useToastStore.getState().addToast({ type: 'error', message: `Disconnect failed: ${err.message}` });
    } finally {
      set({ isDisconnecting: false });
    }
  },
}));
