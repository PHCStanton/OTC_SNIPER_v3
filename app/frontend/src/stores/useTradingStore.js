/**
 * Trading store — trade form state, trade history, execution status.
 */
import { create } from 'zustand';
import { executeTrade, getTrades } from '../api/tradingApi.js';
import { useRiskStore } from './useRiskStore.js';

export const useTradingStore = create((set, get) => ({
  // Form state
  amount: 1,
  direction: 'call', // 'call' | 'put'
  duration: 60,      // seconds
  isGhost: false,

  // Execution state
  isExecuting: false,
  lastTradeResult: null,
  tradeError: null,

  // History
  trades: [],
  isLoadingTrades: false,

  setAmount: (amount) => set({ amount }),
  setDirection: (direction) => set({ direction }),
  setDuration: (duration) => set({ duration }),
  setIsGhost: (val) => set({ isGhost: val }),

  executeTrade: async (broker, asset) => {
    const { amount, direction, duration, isGhost } = get();
    set({ isExecuting: true, tradeError: null, lastTradeResult: null });
    try {
      const result = await executeTrade(broker, {
        asset,
        amount,
        direction,
        duration,
        demo: isGhost,
      });

      const outcome = typeof result?.outcome === 'string' ? result.outcome.trim().toLowerCase() : '';
      const pnl = Number(result?.pnl);

      if (!outcome || !['win', 'loss', 'void'].includes(outcome)) {
        throw new Error('Trade response is missing a valid outcome.');
      }

      if (!Number.isFinite(pnl)) {
        throw new Error('Trade response is missing a numeric pnl.');
      }

      useRiskStore.getState().recordTradeResult({
        outcome,
        pnl,
        stake: amount,
        source: 'auto',
      });

      set({ lastTradeResult: result });
    } catch (err) {
      set({ tradeError: err.message });
    } finally {
      set({ isExecuting: false });
    }
  },

  loadTrades: async (broker) => {
    set({ isLoadingTrades: true });
    try {
      const data = await getTrades(broker);
      set({ trades: data.trades ?? [], tradeError: null });
    } catch (err) {
      set({ tradeError: err.message });
    } finally {
      set({ isLoadingTrades: false });
    }
  },
}));
