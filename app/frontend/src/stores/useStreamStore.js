/**
 * Stream store — live tick data, signal state, manipulation alerts.
 * Updated by Socket.IO market_data and signal events.
 */
import { create } from 'zustand';

export const useStreamStore = create((set) => ({
  // Keyed by asset symbol
  ticks: {},       // { [asset]: TickRecord[] }
  signals: {},     // { [asset]: SignalRecord }
  manipulation: {},// { [asset]: { detected: bool, type: string|null } }
  warmup: {},      // { [asset]: bool }

  // Streaming state
  isStreaming: false,

  setIsStreaming: (val) => set({ isStreaming: val }),

  updateTicks: (asset, ticks) =>
    set((state) => ({
      ticks: { ...state.ticks, [asset]: ticks },
    })),

  updateSignal: (asset, signal) =>
    set((state) => ({
      signals: { ...state.signals, [asset]: signal },
    })),

  updateManipulation: (asset, manipulation) =>
    set((state) => ({
      manipulation: { ...state.manipulation, [asset]: manipulation },
    })),

  setWarmup: (asset, isWarmup) =>
    set((state) => ({
      warmup: { ...state.warmup, [asset]: isWarmup },
    })),

  clearAsset: (asset) =>
    set((state) => {
      const ticks = { ...state.ticks };
      const signals = { ...state.signals };
      const manipulation = { ...state.manipulation };
      const warmup = { ...state.warmup };
      delete ticks[asset];
      delete signals[asset];
      delete manipulation[asset];
      delete warmup[asset];
      return { ticks, signals, manipulation, warmup };
    }),
}));
