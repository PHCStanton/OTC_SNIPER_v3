/**
 * Stream store — live tick data, signal state, manipulation alerts.
/**
 * Stream store — live tick data, signal state, manipulation alerts.
 * Updated by Socket.IO market_data and signal events.
 */
import { create } from 'zustand';

export const EMPTY_TICKS = Object.freeze([]);

export const useStreamStore = create((set) => ({
  // Keyed by asset symbol
  ticks: {},       // { [asset]: TickRecord[] }
  signals: {},     // { [asset]: SignalRecord }
  manipulation: {},// { [asset]: { detected: bool, type: string|null } }
  warmup: {},      // { [asset]: bool }
  tradeMarkers: {},// { [asset]: TradeMarker[] }
  latestPrice: {}, // { [asset]: number } (Phase 2: lightweight updates)

  // Streaming state
  isStreaming: false,

  setIsStreaming: (val) => set({ isStreaming: val }),
  resetAll: () => set({
    ticks: {},
    signals: {},
    manipulation: {},
    warmup: {},
    tradeMarkers: {},
    latestPrice: {},
    isStreaming: false,
  }),

  updateTicks: (asset, ticks) =>
    set((state) => ({
      ticks: { ...state.ticks, [asset]: ticks },
    })),

  // Efficient batch update for multiple assets at once
  batchUpdate: (updates) =>
    set((state) => {
      const nextTicks = { ...state.ticks };
      const nextSignals = { ...state.signals };
      const nextManipulation = { ...state.manipulation };
      const nextLatestPrice = { ...state.latestPrice };
      
      let hasTicks = false;
      let hasSignals = false;
      let hasManip = false;
      let hasLatestPrice = false;

      for (const [asset, data] of Object.entries(updates)) {
        if (data.ticks) {
          nextTicks[asset] = data.ticks;
          hasTicks = true;
        }
        if (data.signal) {
          nextSignals[asset] = data.signal;
          hasSignals = true;
        }
        if (data.manipulation) {
          nextManipulation[asset] = data.manipulation;
          hasManip = true;
        }
        if (data.latestPrice !== undefined) {
          nextLatestPrice[asset] = data.latestPrice;
          hasLatestPrice = true;
        }
      }

      return {
        ...(hasTicks ? { ticks: nextTicks } : {}),
        ...(hasSignals ? { signals: nextSignals } : {}),
        ...(hasManip ? { manipulation: nextManipulation } : {}),
        ...(hasLatestPrice ? { latestPrice: nextLatestPrice } : {}),
      };
    }),

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

  addTradeMarker: (marker) => set((state) => {
    const asset = marker.asset;
    const existing = state.tradeMarkers[asset] || [];
    // Phase 3: Bounding Session Growth (cap to last 50 markers)
    const capped = [...existing, marker].slice(-50);
    return {
      tradeMarkers: {
        ...state.tradeMarkers,
        [asset]: capped,
      },
    };
  }),

  updateTradeMarkerOutcome: (tradeId, outcome, profit) => set((state) => {
    const next = { ...state.tradeMarkers };
    for (const asset of Object.keys(next)) {
      next[asset] = next[asset].map((m) =>
        m.tradeId === tradeId ? { ...m, outcome, profit } : m
      );
    }
    return { tradeMarkers: next };
  }),

  removeExpiredMarkers: (asset) => set((state) => {
    const now = Date.now() / 1000;
    const markers = (state.tradeMarkers[asset] || []).filter(
      (m) => now < m.entryTime + m.expirationSeconds + 30
    );
    return {
      tradeMarkers: { ...state.tradeMarkers, [asset]: markers },
    };
  }),

  clearMarkers: (asset) => set((state) => ({
    tradeMarkers: { ...state.tradeMarkers, [asset]: [] },
  })),

  clearAsset: (asset) =>
    set((state) => {
      const ticks = { ...state.ticks };
      const signals = { ...state.signals };
      const manipulation = { ...state.manipulation };
      const warmup = { ...state.warmup };
      const tradeMarkers = { ...state.tradeMarkers };
      const latestPrice = { ...state.latestPrice };
      delete ticks[asset];
      delete signals[asset];
      delete manipulation[asset];
      delete warmup[asset];
      delete tradeMarkers[asset];
      delete latestPrice[asset];
      return { ticks, signals, manipulation, warmup, tradeMarkers, latestPrice };
    }),
}));
