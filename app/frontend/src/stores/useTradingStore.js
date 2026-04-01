/**
 * Trading store — trade form state, trade history, execution status.
 */
import { create } from 'zustand';
import { executeTrade, getTrades } from '../api/tradingApi.js';
import { useOpsStore } from './useOpsStore.js';
import { useRiskStore } from './useRiskStore.js';
import { useToastStore } from './useToastStore.js';

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
  setLastTradeResult: (value) => set({ lastTradeResult: value }),
  setTradeError: (value) => set({ tradeError: value }),

  executeTrade: async (broker, asset) => {
    const { amount, direction, duration, isGhost } = get();
    set({ isExecuting: true, tradeError: null, lastTradeResult: null });
    try {
      const result = await executeTrade(broker, {
        asset_id: asset,
        amount,
        direction,
        expiration: duration,
        account_key: 'primary',
      });

      if (!result?.success) {
        const message = typeof result?.message === 'string' && result.message.trim().length > 0
          ? result.message
          : 'Trade was rejected before execution.';
        set({ tradeError: message, lastTradeResult: null });
        useToastStore.getState().addToast({ type: 'error', message: `Trade failed: ${message}` });
        return;
      }

      set({ lastTradeResult: result, tradeError: null });
      useToastStore.getState().addToast({ type: 'info', message: 'Trade submitted.' });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      set({ tradeError: message });
      useToastStore.getState().addToast({ type: 'error', message: `Trade failed: ${message}` });
    } finally {
      set({ isExecuting: false });
    }
  },

  loadTrades: async (broker) => {
    set({ isLoadingTrades: true });
    try {
      const sessionId = useOpsStore.getState().sessionId;
      if (!sessionId) {
        throw new Error('No active session ID available. Connect before loading trade history.');
      }

      const data = await getTrades(broker, sessionId);
      const trades = Array.isArray(data) ? data : Array.isArray(data?.trades) ? data.trades : [];
      set({ trades, tradeError: null });
    } catch (err) {
      set({ tradeError: err.message });
      useToastStore.getState().addToast({ type: 'error', message: `Failed to load trades: ${err.message}` });
    } finally {
      set({ isLoadingTrades: false });
    }
  },
}));
