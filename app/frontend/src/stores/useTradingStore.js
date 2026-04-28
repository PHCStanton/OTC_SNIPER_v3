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
import { useAssetStore } from './useAssetStore.js';

function normalizeSignalSnapshot(signal = {}) {
  const oteoScore = Number(signal.oteo_score ?? signal.score ?? 0);

  return {
    price: signal.price ?? null,
    z_score: Number(signal.z_score ?? 0),
    oteo_score: Number.isFinite(oteoScore) ? oteoScore : 0,
    base_oteo_score: Number(signal.base_oteo_score ?? oteoScore ?? 0),
    confidence: Number(signal.confidence ?? 0),
    recommended: signal.recommended ?? signal.direction ?? signal.label ?? null,
    pressure_pct: Number(signal.pressure_pct ?? 0),
    velocity: Number(signal.velocity ?? 0),
    slow_velocity: Number(signal.slow_velocity ?? 0),
    stretch_alignment: Number(signal.stretch_alignment ?? 0),
    level2_enabled: Boolean(signal.level2_enabled),
    level2_score_adjustment: Number(signal.level2_score_adjustment ?? 0),
    level2_suppressed_reason: signal.level2_suppressed_reason ?? null,
    market_context: signal.market_context ?? signal.marketContext ?? null,
  };
}

function validateTradeRequest(asset, amount, duration) {
  const normalizedAsset = typeof asset === 'string' ? asset.trim() : '';
  if (!normalizedAsset) {
    return 'Select an asset before placing a trade.';
  }

  const { availableAssets } = useAssetStore.getState();
  if (Array.isArray(availableAssets) && availableAssets.length > 0 && !availableAssets.includes(normalizedAsset)) {
    return `Selected asset is not available for trading: ${normalizedAsset}`;
  }

  if (!(Number(amount) > 0)) {
    return 'Trade amount must be greater than zero.';
  }

  if (!(Number(duration) > 0)) {
    return 'Trade expiration must be greater than zero.';
  }

  return null;
}

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
    const validationError = validateTradeRequest(asset, finalAmount, duration);

    if (validationError) {
      set({ tradeError: validationError, lastTradeResult: null });
      useToastStore.getState().addToast({ type: 'error', message: validationError });
      return;
    }
    
    // Capture live streaming data (confluences, z-scores, manipulation)
    const { useStreamStore } = await import('./useStreamStore.js');
    const streamState = useStreamStore.getState();
    const signal = streamState.signals[asset] || {};
    const manip = streamState.manipulation[asset] || {};
    const normalizedSignal = normalizeSignalSnapshot(signal);
    
    const entry_context = {
      ...normalizedSignal,
      manipulation: manip.detected ? manip.type : null,
    };
    
    set({ isExecuting: true, tradeError: null, lastTradeResult: null });
    try {
      const result = await executeTrade(broker, {
        asset_id: asset,
        amount: finalAmount,
        direction,
        expiration: duration,
        account_key: 'primary',
        trade_mode: 'live',
        demo: useOpsStore.getState().accountType === 'demo',
        oteo_score: normalizedSignal.oteo_score,
        base_oteo_score: normalizedSignal.base_oteo_score,
        confidence: normalizedSignal.confidence,
        level2_score_adjustment: normalizedSignal.level2_score_adjustment,
        manipulation_at_entry: manip.detected ? { type: manip.type } : null,
        entry_context,
        trigger_mode: 'manual',
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
