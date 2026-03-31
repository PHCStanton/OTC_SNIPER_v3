/**
 * Trading store — trade form state, trade history, execution status.
 */
import { create } from 'zustand';
import { executeTrade, getTrades } from '../api/tradingApi.js';
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

      // Toast feedback for trade outcome
      const pnlLabel = pnl > 0 ? `+$${pnl.toFixed(2)}` : pnl < 0 ? `-$${Math.abs(pnl).toFixed(2)}` : '$0.00';
      if (outcome === 'win') {
        useToastStore.getState().addToast({ type: 'success', message: `WIN — ${pnlLabel}` });
      } else if (outcome === 'loss') {
        useToastStore.getState().addToast({ type: 'error', message: `LOSS — ${pnlLabel}` });
      } else {
        useToastStore.getState().addToast({ type: 'warning', message: 'Trade recorded as VOID.' });
      }
    } catch (err) {
      set({ tradeError: err.message });
      useToastStore.getState().addToast({ type: 'error', message: `Trade failed: ${err.message}` });
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
      useToastStore.getState().addToast({ type: 'error', message: `Failed to load trades: ${err.message}` });
    } finally {
      set({ isLoadingTrades: false });
    }
  },
}));
