/**
 * Asset store — selected asset, live asset list, multi-chart selection.
 *
 * availableAssets: string[] of raw_ids populated from the broker after connect.
 * assetPayouts: map of raw_id → payout fraction (e.g. { 'EURUSD_otc': 0.85 })
 * starredAssets: string[] of raw_ids the user has starred for Quick Select.
 *
 * NOTE: No default asset list — the list is empty until the broker sends live data.
 * This ensures we never show stale or hardcoded assets.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useAssetStore = create()(
  persist(
    (set) => ({
      selectedAsset: 'EURUSD_otc',
      availableAssets: [],
      assetPayouts: {},
      assetDetails: {},
      multiChartAssets: ['EURUSD_otc', 'GBPUSD_otc', 'USDJPY_otc'],
      starredAssets: [],

      setSelectedAsset: (asset) => set({ selectedAsset: asset }),
      setAvailableAssets: (assets) => set({ availableAssets: assets }),
      setAssetPayouts: (payouts) => set({ assetPayouts: payouts }),
      setAssetCatalog: (assets) =>
        set(() => {
          const availableAssets = [];
          const assetPayouts = {};
          const assetDetails = {};

          for (const asset of assets) {
            const rawId = String(asset?.raw_id ?? asset?.id ?? '').trim();
            if (!rawId) continue;
            availableAssets.push(rawId);
            assetDetails[rawId] = {
              raw_id: rawId,
              id: String(asset?.id ?? '').trim(),
              name: String(asset?.name ?? rawId).trim(),
              asset_type: String(asset?.asset_type ?? '').trim().toLowerCase(),
              payout: Number(asset?.payout ?? 0),
              metadata: asset?.metadata && typeof asset.metadata === 'object' ? asset.metadata : {},
            };
            if (asset?.payout != null) {
              assetPayouts[rawId] = Number(asset.payout);
            }
          }

          return { availableAssets, assetPayouts, assetDetails };
        }),
      setMultiChartAssets: (assets) => set({ multiChartAssets: assets.slice(0, 9) }),

      toggleStarredAsset: (asset) =>
        set((state) => {
          const isStarred = state.starredAssets.includes(asset);
          return {
            starredAssets: isStarred
              ? state.starredAssets.filter((a) => a !== asset)
              : [...state.starredAssets, asset],
          };
        }),

      addMultiChartAsset: (asset) =>
        set((state) => {
          if (state.multiChartAssets.includes(asset)) return state;
          if (state.multiChartAssets.length >= 9) return state;
          return { multiChartAssets: [...state.multiChartAssets, asset] };
        }),

      removeMultiChartAsset: (asset) =>
        set((state) => ({
          multiChartAssets: state.multiChartAssets.filter((a) => a !== asset),
        })),
    }),
    {
      name: 'otc-sniper-asset-storage',
      // Only persist starred assets and selected asset — NOT the asset list itself.
      // The asset list must always be refreshed from the broker on connect.
      partialize: (state) => ({
        selectedAsset: state.selectedAsset,
        starredAssets: state.starredAssets,
        multiChartAssets: state.multiChartAssets,
      }),
    }
  )
);
