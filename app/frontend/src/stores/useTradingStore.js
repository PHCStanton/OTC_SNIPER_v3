/**
 * Trading store — trade form state, trade history, execution status.
 */
import { create } from 'zustand';
import { executeTrade, getTrades } from '../api/tradingApi.js';

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
      set({ trades: data.trades ?? [] });
    } catch (err) {
      console.error('[useTradingStore] loadTrades error:', err.message);
    } finally {
      set({ isLoadingTrades: false });
    }
  },
}));
