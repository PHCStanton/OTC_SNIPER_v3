/**
 * Auth store — SSID input state and connect/disconnect actions.
 * Wraps opsApi calls and syncs result into useOpsStore.
 */
import { create } from 'zustand';
import { getBrokerAssets } from '../api/tradingApi.js';
import { sessionConnect, sessionDisconnect } from '../api/opsApi.js';
import { useAssetStore } from './useAssetStore.js';
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
      ops.setSessionId(data.session_id ?? null);
      if (data.balance != null) ops.setBalance(data.balance);
      if (data.account_type != null) ops.setAccountType(data.account_type);
      set({ ssidInput: '', connectError: null });
      const accountLabel = (data.account_type ?? (demo ? 'demo' : 'real')).toUpperCase();
      useToastStore.getState().addToast({ type: 'success', message: `Session connected — ${accountLabel} account` });

      try {
        const assetsData = await getBrokerAssets('pocket_option');
        const rawAssets = Array.isArray(assetsData?.assets) ? assetsData.assets : [];

        const assetIds = rawAssets
          .map((asset) => String(asset?.raw_id ?? asset?.id ?? '').trim())
          .filter((assetId) => assetId.length > 0);

        // Build payout map: raw_id → payout fraction (e.g. 'EURUSD_otc' → 0.85)
        const payoutMap = {};
        for (const asset of rawAssets) {
          const key = String(asset?.raw_id ?? asset?.id ?? '').trim();
          if (key && asset?.payout != null) {
            payoutMap[key] = Number(asset.payout);
          }
        }

        if (assetIds.length > 0) {
          const assetStore = useAssetStore.getState();
          assetStore.setAvailableAssets(assetIds);
          assetStore.setAssetPayouts(payoutMap);
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
      useToastStore.getState().addToast({ type: 'info', message: 'Session disconnected.' });
    } catch (err) {
      set({ connectError: err.message });
      useToastStore.getState().addToast({ type: 'error', message: `Disconnect failed: ${err.message}` });
    } finally {
      set({ isDisconnecting: false });
    }
  },
}));
