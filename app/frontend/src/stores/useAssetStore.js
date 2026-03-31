/**
 * Asset store — selected asset, OTC asset list, multi-chart selection.
 *
 * assetPayouts: map of raw_id → payout fraction (e.g. { 'EURUSD_otc': 0.85 })
 * Populated after a successful broker connect from the /api/brokers/pocket_option/assets response.
 * availableAssets remains a string[] of raw_ids for backward compatibility with all consumers.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Default OTC assets (mirrors backend assets.py)
const DEFAULT_ASSETS = [
  'EURUSD_otc', 'GBPUSD_otc', 'USDJPY_otc', 'AUDUSD_otc',
  'USDCAD_otc', 'USDCHF_otc', 'EURGBP_otc', 'EURJPY_otc',
  'GBPJPY_otc', 'NZDUSD_otc', 'AUDCAD_otc', 'AUDCHF_otc',
  'CADJPY_otc',
];

export const useAssetStore = create()(
  persist(
    (set) => ({
      selectedAsset: 'EURUSD_otc',
      availableAssets: DEFAULT_ASSETS,
      /** map of raw_id → payout fraction, e.g. { 'EURUSD_otc': 0.85 } */
      assetPayouts: {},
      multiChartAssets: ['EURUSD_otc', 'GBPUSD_otc', 'USDJPY_otc'],

      setSelectedAsset: (asset) => set({ selectedAsset: asset }),
      setAvailableAssets: (assets) => set({ availableAssets: assets }),
      /** Store payout fractions keyed by raw_id. */
      setAssetPayouts: (payouts) => set({ assetPayouts: payouts }),
      setMultiChartAssets: (assets) => set({ multiChartAssets: assets.slice(0, 9) }),

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
    { name: 'otc-sniper-asset-storage' }
  )
);
