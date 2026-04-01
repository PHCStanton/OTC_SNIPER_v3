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
      /** map of raw_id → payout fraction, e.g. { 'EURUSD_otc': 0.85 } */
      assetPayouts: {},
      multiChartAssets: ['EURUSD_otc', 'GBPUSD_otc', 'USDJPY_otc'],
      /** list of raw_ids for starred/favorite assets (Quick Select) */
      starredAssets: [],

      setSelectedAsset: (asset) => set({ selectedAsset: asset }),
      setAvailableAssets: (assets) => set({ availableAssets: assets }),
      /** Store payout fractions keyed by raw_id. */
      setAssetPayouts: (payouts) => set({ assetPayouts: payouts }),
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
