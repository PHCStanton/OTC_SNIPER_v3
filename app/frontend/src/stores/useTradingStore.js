/**
 * Trading store — trade form state, trade history, execution status.
 */
import { create } from 'zustand';
import { executeTrade, getTrades } from '../api/tradingApi.js';
import { getRuntimeStrategyConfig } from '../api/strategyApi.js';
import { useOpsStore } from './useOpsStore.js';
import { useRiskStore } from './useRiskStore.js';
import { useToastStore } from './useToastStore.js';
import { useSettingsStore } from './useSettingsStore.js';

export const useTradingStore = create((set, get) => ({
  // Form state
  amount: 20,
  direction: 'call', // 'call' | 'put'
  duration: 60,      // seconds

  // Execution state
  isExecuting: false,
  lastTradeResult: null,
  tradeError: null,

  // History
  trades: [],
  isLoadingTrades: false,
  tradeHistoryMode: 'live', // 'live' | 'ghost'

  setAmount: (amount) => set({ amount }),
  setDirection: (direction) => set({ direction }),
  setDuration: (duration) => set({ duration }),
  setLastTradeResult: (value) => set({ lastTradeResult: value }),
  setTradeError: (value) => set({ tradeError: value }),
  setTradeHistoryMode: (mode) => {
    set({ tradeHistoryMode: mode });
    get().loadTrades('pocket_option');
  },

  executeTrade: async (broker, asset, overrideAmount = null) => {
    const { amount, direction, duration } = get();
    const finalAmount = overrideAmount !== null ? overrideAmount : amount;
    
    set({ isExecuting: true, tradeError: null, lastTradeResult: null });
    try {
      const result = await executeTrade(broker, {
        asset_id: asset,
        amount: finalAmount,
        direction,
        expiration: duration,
        account_key: 'primary',
        trade_mode: 'live',
        demo: false,
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

      const assetLabel = typeof asset === 'string' ? asset.replace(/_otc$/i, ' OTC').replace(/_/g, '/') : String(asset);
      const expiryLabel = duration === 60 ? '1M' : `${duration}s`;
      const message = `Trade submitted [${direction.toUpperCase()}]: ${assetLabel} | Expiry: ${expiryLabel}`;

      useToastStore.getState().addToast({ type: 'info', message });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      set({ tradeError: message });
      useToastStore.getState().addToast({ type: 'error', message: `Trade failed: ${message}` });
    } finally {
      set({ isExecuting: false });
    }
  },

  loadTrades: async (broker) => {
    set({ isLoadingTrades: true, trades: [] }); 
    // Artificial delay to ensure UI loading pulse is perceptible because local file reads are too fast
    await new Promise(r => setTimeout(r, 400));
    try {
      const mode = get().tradeHistoryMode;
      let targetSessionId = null;

      if (mode === 'live') {
        targetSessionId = useOpsStore.getState().sessionId;
        if (!targetSessionId) {
          throw new Error('No active session ID available.');
        }
      } else if (mode === 'ghost') {
        const config = await getRuntimeStrategyConfig();
        targetSessionId = config?.auto_ghost_session_id;
        if (!targetSessionId) {
          throw new Error('No ghost session active.');
        }
      }

      const data = await getTrades(broker, targetSessionId);
      const trades = Array.isArray(data) ? data : Array.isArray(data?.trades) ? data.trades : [];
      set({ trades, tradeError: null });
    } catch (err) {
      set({ tradeError: err.message, trades: [] });
      useToastStore.getState().addToast({ type: 'error', message: `Failed to load ${get().tradeHistoryMode} trades: ${err.message}` });
    } finally {
      set({ isLoadingTrades: false });
    }
  },
}));
