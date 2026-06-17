import { useEffect } from 'react';
import { initSocket } from './api/socketClient.js';
import { updateRuntimeStrategyConfig } from './api/strategyApi.js';
import { useStreamConnection } from './hooks/useStreamConnection.js';
import { useLayoutStore } from './stores/useLayoutStore.js';
import { useAssetStore } from './stores/useAssetStore.js';
import { useOpsStore } from './stores/useOpsStore.js';
import { useRiskStore } from './stores/useRiskStore.js';
import { useSettingsStore } from './stores/useSettingsStore.js';
import { useToastStore } from './stores/useToastStore.js';
import { useTradingStore } from './stores/useTradingStore.js';
import { useStreamStore } from './stores/useStreamStore.js';
import { soundManager } from './utils/soundUtils.js';
import MainLayout from './components/layout/MainLayout.jsx';
import ErrorBoundary from './components/shared/ErrorBoundary.jsx';
import ComponentsPage from './components/dev/ComponentsPage.jsx';
import { useNotificationStore } from './stores/useNotificationStore.js';

const VALID_TRADE_OUTCOMES = new Set(['win', 'loss', 'void']);

export default function App() {
  const dashboardMode = useLayoutStore((s) => s.dashboardMode);
  const { setChromeStatus, setSessionStatus, setSessionId, setBalance, setAccountType } = useOpsStore();
  const oteoLevel2Enabled = useSettingsStore((s) => s.oteoLevel2Enabled);
  const oteoLevel3Enabled = useSettingsStore((s) => s.oteoLevel3Enabled);
  const oteoAiEnabled = useSettingsStore((s) => s.oteoAiEnabled);
  const ghostAmount = useSettingsStore((s) => s.ghostAmount);
  const autoGhostEnabled = useSettingsStore((s) => s.autoGhostEnabled);
  const autoGhostExpirationSeconds = useSettingsStore((s) => s.autoGhostExpirationSeconds);
  const autoGhostMaxConcurrentTrades = useSettingsStore((s) => s.autoGhostMaxConcurrentTrades);
  const autoGhostPerAssetCooldownSeconds = useSettingsStore((s) => s.autoGhostPerAssetCooldownSeconds);
  const autoGhostMaxSessionTrades = useSettingsStore((s) => s.autoGhostMaxSessionTrades);
  const autoGhostMaxDrawdownAmount = useSettingsStore((s) => s.autoGhostMaxDrawdownAmount);
  const autoGhostDrawdownCooldownSeconds = useSettingsStore((s) => s.autoGhostDrawdownCooldownSeconds);
  const autoGhostMinimumPayout = useSettingsStore((s) => s.autoGhostMinimumPayout);
  const autoGhostManipulationSeverityThreshold = useSettingsStore((s) => s.autoGhostManipulationSeverityThreshold);
  const autoGhostBlockOnManipulation = useSettingsStore((s) => s.autoGhostBlockOnManipulation);
  const ghostMaxTradesPerTimeframe = useSettingsStore((s) => s.ghostMaxTradesPerTimeframe);
  const ghostTimeframeSeconds = useSettingsStore((s) => s.ghostTimeframeSeconds);
  const ghostMinConfidence = useSettingsStore((s) => s.ghostMinConfidence);
  const ghostMinConfidenceEnabled = useSettingsStore((s) => s.ghostMinConfidenceEnabled);
  const ghostMaxConfidence = useSettingsStore((s) => s.ghostMaxConfidence);
  const ghostMaxConfidenceEnabled = useSettingsStore((s) => s.ghostMaxConfidenceEnabled);
  const oteoAiExecutionMode = useSettingsStore((s) => s.oteoAiExecutionMode);
  const ghostMinZScore = useSettingsStore((s) => s.ghostMinZScore);
  const ghostMinZScoreEnabled = useSettingsStore((s) => s.ghostMinZScoreEnabled);
  const ghostMaxZScore = useSettingsStore((s) => s.ghostMaxZScore);
  const ghostMaxZScoreEnabled = useSettingsStore((s) => s.ghostMaxZScoreEnabled);
  const ghostRegimeGateEnabled = useSettingsStore((s) => s.ghostRegimeGateEnabled);
  const ghostAllowedRegimes = useSettingsStore((s) => s.ghostAllowedRegimes);
  const ghostRequireRegimeStable = useSettingsStore((s) => s.ghostRequireRegimeStable);

  // New AI advisory settings
  const aiTradeInterval = useSettingsStore((s) => s.aiTradeInterval);
  const aiPulseEnabled = useSettingsStore((s) => s.aiPulseEnabled);
  const aiPulseIntervalSeconds = useSettingsStore((s) => s.aiPulseIntervalSeconds);


  useStreamConnection();

  // Connect Socket.IO on mount and start status polling
  useEffect(() => {
    // Global UI Click Listener
    const handleGlobalClick = (e) => {
      // Trigger sound for buttons, select, and links
      const isInteractive = e.target.closest('button, a, select, input[type="checkbox"], input[type="radio"]');
      if (isInteractive) {
        soundManager.playClick();
      }
    };
    window.addEventListener('click', handleGlobalClick, { capture: true });

    const socket = initSocket();

    socket.on('status_update', (data) => {
      if (data.chrome) {
        setChromeStatus(data.chrome.running ? 'running' : 'stopped');
      }
      if (data.session) {
        setSessionStatus(data.session.connected ? 'connected' : 'disconnected');
        setSessionId(data.session.session_id ?? null);
        if (data.session.balance != null) setBalance(data.session.balance);
        if (data.session.account_type != null) setAccountType(data.session.account_type);
      }
      if (data.auto_ghost) {
        useRiskStore.getState().setAutoGhostMetrics(data.auto_ghost);
      }
    });

    socket.on('trade_entry', (data) => {
      useStreamStore.getState().addTradeMarker({
        tradeId: data.trade_id,
        asset: data.asset,
        direction: data.direction,
        kind: data.kind,
        entryPrice: data.entry_price,
        entryTime: data.entry_time,
        expirationSeconds: data.expiration_seconds,
        amount: data.amount,
        outcome: null,
        profit: null,
      });

      if (data.kind === 'ghost') {
        useRiskStore.getState().recordGhostTradeEntry({
          tradeId: data.trade_id,
          asset: data.asset,
          direction: data.direction,
          entryPrice: data.entry_price,
          entryTime: data.entry_time,
          expirationSeconds: data.expiration_seconds,
          amount: data.amount,
          oteoScore: data.oteo_score,
        });
      }

      if (data.trigger_mode === 'auto_ghost' || data.trigger_mode === 'auto') {
        const assetLabel = typeof data.asset === 'string' ? data.asset.replace(/_otc$/i, ' OTC').replace(/_/g, '/') : String(data.asset);
        const expiryLabel = data.expiration_seconds === 60 ? '1M' : `${data.expiration_seconds}s`;
        const prefix = data.kind === 'ghost' ? 'Auto-Ghost trade' : 'Auto trade';
        
        const toastMessage = `${prefix} [${data.direction.toUpperCase()}] executed: ${assetLabel} | Expiry: ${expiryLabel}`;
        
        const onDoubleClick = data.kind === 'ghost' ? () => {
          const { autoGhostCopyMode } = useSettingsStore.getState();
          useAssetStore.getState().setSelectedAsset(data.asset);
          
          useToastStore.getState().addToast({
            type: 'success',
            message: `Selected Ghost Asset: ${assetLabel}`,
            duration: 3000
          });

          if (autoGhostCopyMode === 'execute') {
            useTradingStore.getState().setDirection(data.direction);
            useTradingStore.getState().setDuration(data.expiration_seconds);
            useTradingStore.getState().executeTrade('pocket_option', data.asset);
          }
        } : undefined;

        useToastStore.getState().addToast({ 
          type: 'info', 
          message: toastMessage,
          onDoubleClick
        });

        if (data.kind === 'ghost') {
          soundManager.playGhostExecute();
        }
      }
    });

    socket.on('trade_result', (data) => {
      const outcome = typeof data?.outcome === 'string' ? data.outcome.trim().toLowerCase() : '';
      const tradeKind = typeof data?.kind === 'string' ? data.kind.trim().toLowerCase() : 'live';
      const tradeSource = tradeKind === 'ghost' ? 'ghost' : 'live';
      if (!VALID_TRADE_OUTCOMES.has(outcome)) {
        useTradingStore.getState().setLastTradeResult(data);
        useToastStore.getState().addToast({ type: 'info', message: 'Trade result received.' });
        return;
      }

      const profit = Number(data?.profit);
      const stake = Number(data?.amount ?? 0);
      const pnl = Number.isFinite(profit) ? profit : 0;

      useTradingStore.getState().setLastTradeResult({
        ...data,
        outcome,
        pnl,
        kind: tradeKind,
      });

      useRiskStore.getState().recordTradeResult({
        outcome,
        pnl,
        stake,
        payoutPercentage: data?.payout_pct,
        source: tradeSource,
        tradeId: data?.trade_id,
        sessionId: data?.session_id,
        asset: data?.asset,
        direction: data?.direction,
        expirationSeconds: data?.expiration_seconds,
        confidence: data?.confidence,
        oteoScore: data?.oteo_score,
        baseOteoScore: data?.base_oteo_score,
        baseConfidence: data?.base_confidence,
        level2ScoreAdjustment: data?.level2_score_adjustment,
        level3ScoreAdjustment: data?.level3_score_adjustment,
        strategyLevel: data?.strategy_level,
        triggerMode: data?.trigger_mode,
        entryPrice: data?.entry_price,
        entryTime: data?.entry_time,
        exitPrice: data?.exit_price,
        exitTime: data?.exit_time,
        zScore: data?.z_score,
        manipulation: data?.manipulation,
      });

      if (data?.asset && (outcome === 'win' || outcome === 'loss')) {
        useRiskStore.getState().recordAssetTrade(data.asset, outcome);
      }
      
      if (data?.trade_id) {
        useStreamStore.getState().updateTradeMarkerOutcome(
          data.trade_id,
          outcome,
          pnl
        );
      }

      const pnlLabel = pnl > 0 ? `+$${pnl.toFixed(2)}` : pnl < 0 ? `-$${Math.abs(pnl).toFixed(2)}` : '$0.00';
      const prefix = tradeKind === 'ghost' ? 'GHOST ' : '';
      if (outcome === 'win') {
        useToastStore.getState().addToast({ type: 'success', message: `${prefix}WIN — ${pnlLabel}` });
        if (tradeKind === 'ghost') soundManager.playGhostWin();
      } else if (outcome === 'loss') {
        useToastStore.getState().addToast({ type: 'error', message: `${prefix}LOSS — ${pnlLabel}` });
        if (tradeKind === 'ghost') soundManager.playGhostLoss();
      } else {
        useToastStore.getState().addToast({ type: 'warning', message: `${prefix}trade recorded as VOID.` });
      }
    });

    socket.on('notification', (data) => {
      useNotificationStore.getState().addNotification({
        type: data.type || 'info',
        message: data.message,
        timestamp: data.timestamp,
        suggestions: data.suggestions || null,
      });

      useToastStore.getState().addToast({
        type: data.type === 'warning' ? 'warning' : 'info',
        message: data.message,
        duration: 6000,
      });

      soundManager.playNotification();
    });

    // Poll every 5 seconds
    const poll = () => socket.emit('check_status');
    poll();
    const interval = setInterval(poll, 5000);

    return () => {
      window.removeEventListener('click', handleGlobalClick, { capture: true });
      clearInterval(interval);
      socket.off('status_update');
      socket.off('trade_entry');
      socket.off('trade_result');
      socket.off('notification');
    };
  }, [setChromeStatus, setSessionStatus, setSessionId, setBalance, setAccountType]);

  useEffect(() => {
    let isMounted = true;

    const syncRuntimeConfig = async () => {
      try {
        await updateRuntimeStrategyConfig({
          oteo_level2_enabled: oteoLevel2Enabled,
          oteo_level3_enabled: oteoLevel3Enabled,
          oteo_ai_enabled: oteoAiEnabled,
          oteo_ai_execution_mode: oteoAiExecutionMode,
          auto_ghost_enabled: autoGhostEnabled,
          auto_ghost_amount: ghostAmount,
          auto_ghost_expiration_seconds: autoGhostExpirationSeconds,
          auto_ghost_max_concurrent_trades: autoGhostMaxConcurrentTrades,
          auto_ghost_per_asset_cooldown_seconds: autoGhostPerAssetCooldownSeconds,
          auto_ghost_max_session_trades: autoGhostMaxSessionTrades,
          auto_ghost_max_drawdown_amount: autoGhostMaxDrawdownAmount,
          auto_ghost_drawdown_cooldown_seconds: autoGhostDrawdownCooldownSeconds,
          auto_ghost_minimum_payout: autoGhostMinimumPayout / 100,
          auto_ghost_manipulation_severity_threshold: autoGhostManipulationSeverityThreshold,
          auto_ghost_block_on_manipulation: autoGhostBlockOnManipulation,
          auto_ghost_max_trades_per_timeframe: ghostMaxTradesPerTimeframe,
          auto_ghost_timeframe_seconds: ghostTimeframeSeconds,
          auto_ghost_min_confidence: ghostMinConfidenceEnabled ? ghostMinConfidence : null,
          auto_ghost_min_confidence_enabled: ghostMinConfidenceEnabled,
          auto_ghost_max_confidence: ghostMaxConfidenceEnabled ? ghostMaxConfidence : null,
          auto_ghost_max_confidence_enabled: ghostMaxConfidenceEnabled,
          auto_ghost_min_zscore: ghostMinZScoreEnabled ? ghostMinZScore : null,
          auto_ghost_min_zscore_enabled: ghostMinZScoreEnabled,
          auto_ghost_max_zscore: ghostMaxZScoreEnabled ? ghostMaxZScore : null,
          auto_ghost_max_zscore_enabled: ghostMaxZScoreEnabled,
          auto_ghost_regime_gate_enabled: ghostRegimeGateEnabled,
          auto_ghost_allowed_regimes: ghostAllowedRegimes,
          auto_ghost_require_regime_stable: ghostRequireRegimeStable,
          ai_trade_interval: aiTradeInterval,
          ai_pulse_enabled: aiPulseEnabled,
          ai_pulse_interval_seconds: aiPulseIntervalSeconds,
        });
      } catch (err) {
        if (isMounted) {
          console.warn('[App] Failed to sync runtime strategy config:', err.message);
        }
      }
    };

    const timer = setTimeout(() => {
      void syncRuntimeConfig();
    }, 400);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [
    oteoLevel2Enabled,
    oteoLevel3Enabled,
    oteoAiEnabled,
    oteoAiExecutionMode,
    ghostAmount,
    autoGhostEnabled,
    autoGhostExpirationSeconds,
    autoGhostMaxConcurrentTrades,
    autoGhostPerAssetCooldownSeconds,
    autoGhostMaxSessionTrades,
    autoGhostMaxDrawdownAmount,
    autoGhostDrawdownCooldownSeconds,
    autoGhostMinimumPayout,
    autoGhostManipulationSeverityThreshold,
    autoGhostBlockOnManipulation,
    ghostMaxTradesPerTimeframe,
    ghostTimeframeSeconds,
    ghostMinConfidence,
    ghostMinConfidenceEnabled,
    ghostMaxConfidence,
    ghostMaxConfidenceEnabled,
    ghostMinZScore,
    ghostMinZScoreEnabled,
    ghostMaxZScore,
    ghostMaxZScoreEnabled,
    ghostRegimeGateEnabled,
    ghostAllowedRegimes,
    ghostRequireRegimeStable,
    aiTradeInterval,
    aiPulseEnabled,
    aiPulseIntervalSeconds,
  ]);

  return (
    <div className="dark" data-dashboard-mode={dashboardMode}>
      <ErrorBoundary label="Application">
        {window.location.pathname === '/components' ? <ComponentsPage /> : <MainLayout />}
      </ErrorBoundary>
    </div>
  );
}
