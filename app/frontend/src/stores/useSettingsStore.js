/**
 * Settings store — app-level configuration (not account/session).
 * Persisted to localStorage.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const SETTINGS_DEFAULTS = {
  // OTEO configuration
  oteoEnabled: true,
  oteoLevel2Enabled: false,
  oteoLevel3Enabled: false,
  oteoAiEnabled: false,
  oteoWarmupBars: 20,
  oteoCooldownBars: 3,

  // Ghost trading
  ghostAmount: 20,
  autoGhostEnabled: false,
  autoGhostCopyMode: 'copy', // 'copy' | 'execute'
  autoGhostExpirationSeconds: 60,
  autoGhostMaxConcurrentTrades: 3,
  autoGhostPerAssetCooldownSeconds: 30,
  autoGhostMaxSessionTrades: 100,
  autoGhostMaxDrawdownAmount: 100,
  autoGhostDrawdownCooldownSeconds: 300,
  autoGhostMinimumPayout: 88,
  autoGhostManipulationSeverityThreshold: 0.0,
  autoGhostBlockOnManipulation: true,
  ghostWidgetPosition: { x: 0, y: 0 },
  ghostIcon: 'drift.gif',
  ghostMaxTradesPerTimeframe: 2,
  ghostTimeframeSeconds: 60,
  ghostMinConfidence: 75,
  ghostMinConfidenceEnabled: true,
  ghostMaxConfidence: 95,
  ghostMaxConfidenceEnabled: false,

  // Ghost Z-Score & Regime gates (Ghost Protocol)
  ghostMinZScore: -0.5,
  ghostMinZScoreEnabled: false,
  ghostMaxZScore: 1.5,
  ghostMaxZScoreEnabled: false,
  ghostRegimeGateEnabled: false,
  ghostAllowedRegimes: [],
  ghostRequireRegimeStable: false,
  ghostProtocols: null,
  activeGhostProtocol: 'default',

  // Hurst Filter (L1 Core) & Package license gates
  hurstFilterEnabled: false,
  hurstFilterThreshold: 0.48,
  hasPremiumHurst: false,
  hasEliteHurst: false,
  hurstMeanRevertThreshold: 0.44,
  hurstTrendThreshold: 0.58,
  minAdaptiveExpiry: 60,
  hurstMinScaleCutoff: 12,
  hurstAiConfidenceThreshold: 80,

  // Trade Markers
  showGhostEntryMarkers: true,
  showLiveEntryMarkers: true,

  // Session risk defaults
  initialBalance: 1000,
  payoutPercentage: 80,
  riskPercentPerTrade: 1,
  drawdownPercent: 10,
  riskRewardRatio: 2,
  useFixedAmount: false,
  fixedRiskAmount: 20,
  tradesPerRun: 4,
  maxRuns: 3,

  // Risk management
  maxDailyLoss: 50,
  maxTradesPerSession: 20,
  stopOnLossStreak: 3,

  // AI integration (see dedicated AI Settings for full profiles + voices)
  aiModel: 'grok-4.3-fast',
  aiDevMode: false,
  oteoAiExecutionMode: 'advisory',
  aiTradeInterval: 10,
  aiPulseEnabled: false,
  aiPulseIntervalSeconds: 120,


  // Rich AI Profiles (dedicated AI tab) — easy add/remove/manage various settings + voices here
  // voice now supports Grok Native TTS:
  // provider: 'browser' | 'grok'
  // voiceId: 'eve' | 'ara' | 'rex' | 'sal' | 'leo' | custom_id  (for grok)
  // speed, language for Grok TTS; rate/pitch/volume for browser
  aiProfiles: null,
  activeAiProfile: 'default',
  featureProfiles: {
    confirmation: 'default',
    review: 'deep-review',
    analysis: 'deep-review',
    chat: 'default',
    voiceover: 'deep-review',
  },

  // UI preferences
  showManipulationAlerts: true,
  showSignalConfidence: true,
  autoFocusOnSignal: false,

  // Data Feeds
  assetAutoRefreshEnabled: false,
  assetAutoRefreshInterval: 60,

  // Mini-Chart Modular Configuration
  miniChartConfig: {
    showSparkline: true,
    showGauge: true,
    gaugeOnHover: false,
    showStats: true,
    showRegime: true,
    showManipulation: true,
  },
  uiSoundsEnabled: true,
  tradingSoundsEnabled: true,
  notificationSoundsEnabled: true,
  dontDisturbEnabled: false,
  showGlobalTimer: false,
};

function toBoolean(value, fallback = false) {
  if (typeof value === 'boolean') return value;
  return fallback;
}

function toNumber(value, fallback, { min = Number.NEGATIVE_INFINITY, max = Number.POSITIVE_INFINITY, integer = false } = {}) {
  if (value === '' || value === null || value === undefined) return fallback;

  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;

  const clamped = Math.min(max, Math.max(min, parsed));
  return integer ? Math.trunc(clamped) : clamped;
}

function toPosition(value, fallback = { x: 0, y: 0 }) {
  if (!value || typeof value !== 'object') return fallback;
  return {
    x: typeof value.x === 'number' && Number.isFinite(value.x) ? value.x : fallback.x,
    y: typeof value.y === 'number' && Number.isFinite(value.y) ? value.y : fallback.y,
  };
}

export function validateSettings(input = {}) {
  const oteoLevel2Enabled = toBoolean(input.oteoLevel2Enabled, SETTINGS_DEFAULTS.oteoLevel2Enabled);
  const oteoLevel3Requested = toBoolean(input.oteoLevel3Enabled, SETTINGS_DEFAULTS.oteoLevel3Enabled);
  const oteoLevel3Enabled = oteoLevel2Enabled ? oteoLevel3Requested : false;

  return {
    oteoEnabled: true,
    oteoLevel2Enabled,
    oteoLevel3Enabled,
    oteoAiEnabled: toBoolean(input.oteoAiEnabled, SETTINGS_DEFAULTS.oteoAiEnabled),
    oteoWarmupBars: toNumber(input.oteoWarmupBars, SETTINGS_DEFAULTS.oteoWarmupBars, { min: 0, max: 500, integer: true }),
    oteoCooldownBars: toNumber(input.oteoCooldownBars, SETTINGS_DEFAULTS.oteoCooldownBars, { min: 0, max: 500, integer: true }),

    ghostAmount: toNumber(input.ghostAmount, SETTINGS_DEFAULTS.ghostAmount, { min: 0, max: 100000, integer: false }),
    autoGhostEnabled: toBoolean(input.autoGhostEnabled, SETTINGS_DEFAULTS.autoGhostEnabled),
    autoGhostCopyMode: ['copy', 'execute'].includes(input.autoGhostCopyMode) ? input.autoGhostCopyMode : 'copy',
    autoGhostExpirationSeconds: toNumber(input.autoGhostExpirationSeconds, SETTINGS_DEFAULTS.autoGhostExpirationSeconds, { min: 5, max: 3600, integer: true }),
    autoGhostMaxConcurrentTrades: toNumber(input.autoGhostMaxConcurrentTrades, SETTINGS_DEFAULTS.autoGhostMaxConcurrentTrades, { min: 1, max: 20, integer: true }),
    autoGhostPerAssetCooldownSeconds: toNumber(input.autoGhostPerAssetCooldownSeconds, SETTINGS_DEFAULTS.autoGhostPerAssetCooldownSeconds, { min: 0, max: 3600, integer: true }),
    autoGhostMaxSessionTrades: toNumber(input.autoGhostMaxSessionTrades, SETTINGS_DEFAULTS.autoGhostMaxSessionTrades, { min: 1, max: 10000, integer: true }),
    autoGhostMaxDrawdownAmount: toNumber(input.autoGhostMaxDrawdownAmount, SETTINGS_DEFAULTS.autoGhostMaxDrawdownAmount, { min: 0, max: 100000, integer: false }),
    autoGhostDrawdownCooldownSeconds: toNumber(input.autoGhostDrawdownCooldownSeconds, SETTINGS_DEFAULTS.autoGhostDrawdownCooldownSeconds, { min: 0, max: 36000, integer: true }),
    autoGhostMinimumPayout: toNumber(input.autoGhostMinimumPayout, SETTINGS_DEFAULTS.autoGhostMinimumPayout, { min: 0, max: 100, integer: false }),
    autoGhostManipulationSeverityThreshold: toNumber(input.autoGhostManipulationSeverityThreshold, SETTINGS_DEFAULTS.autoGhostManipulationSeverityThreshold, { min: 0.0, max: 1.0, integer: false }),
    autoGhostBlockOnManipulation: toBoolean(input.autoGhostBlockOnManipulation, SETTINGS_DEFAULTS.autoGhostBlockOnManipulation),
    ghostWidgetPosition: toPosition(input.ghostWidgetPosition, SETTINGS_DEFAULTS.ghostWidgetPosition),
    ghostIcon: typeof input.ghostIcon === 'string' && input.ghostIcon.trim()
      ? input.ghostIcon.trim()
      : SETTINGS_DEFAULTS.ghostIcon,
    ghostMaxTradesPerTimeframe: toNumber(input.ghostMaxTradesPerTimeframe, SETTINGS_DEFAULTS.ghostMaxTradesPerTimeframe, { min: 1, max: 100, integer: true }),
    ghostTimeframeSeconds: toNumber(input.ghostTimeframeSeconds, SETTINGS_DEFAULTS.ghostTimeframeSeconds, { min: 5, max: 3600, integer: true }),
    ghostMinConfidence: toNumber(input.ghostMinConfidence, SETTINGS_DEFAULTS.ghostMinConfidence, { min: 50, max: 100, integer: true }),
    ghostMinConfidenceEnabled: toBoolean(input.ghostMinConfidenceEnabled, SETTINGS_DEFAULTS.ghostMinConfidenceEnabled),
    ghostMaxConfidence: toNumber(input.ghostMaxConfidence, SETTINGS_DEFAULTS.ghostMaxConfidence, { min: 50, max: 100, integer: true }),
    ghostMaxConfidenceEnabled: toBoolean(input.ghostMaxConfidenceEnabled, SETTINGS_DEFAULTS.ghostMaxConfidenceEnabled),

    ghostMinZScore: toNumber(input.ghostMinZScore, SETTINGS_DEFAULTS.ghostMinZScore, { min: -3.0, max: 3.0, integer: false }),
    ghostMinZScoreEnabled: toBoolean(input.ghostMinZScoreEnabled, SETTINGS_DEFAULTS.ghostMinZScoreEnabled),
    ghostMaxZScore: toNumber(input.ghostMaxZScore, SETTINGS_DEFAULTS.ghostMaxZScore, { min: -3.0, max: 3.0, integer: false }),
    ghostMaxZScoreEnabled: toBoolean(input.ghostMaxZScoreEnabled, SETTINGS_DEFAULTS.ghostMaxZScoreEnabled),
    ghostRegimeGateEnabled: toBoolean(input.ghostRegimeGateEnabled, SETTINGS_DEFAULTS.ghostRegimeGateEnabled),
    ghostAllowedRegimes: Array.isArray(input.ghostAllowedRegimes) ? input.ghostAllowedRegimes : SETTINGS_DEFAULTS.ghostAllowedRegimes,
    ghostRequireRegimeStable: toBoolean(input.ghostRequireRegimeStable, SETTINGS_DEFAULTS.ghostRequireRegimeStable),
    ghostProtocols: input.ghostProtocols && typeof input.ghostProtocols === 'object' ? input.ghostProtocols : null,
    activeGhostProtocol: typeof input.activeGhostProtocol === 'string' ? input.activeGhostProtocol : 'default',

    hurstFilterEnabled: toBoolean(input.hurstFilterEnabled, SETTINGS_DEFAULTS.hurstFilterEnabled),
    hurstFilterThreshold: toNumber(input.hurstFilterThreshold, SETTINGS_DEFAULTS.hurstFilterThreshold, { min: 0.0, max: 1.0, integer: false }),
    hasPremiumHurst: toBoolean(input.hasPremiumHurst, SETTINGS_DEFAULTS.hasPremiumHurst),
    hasEliteHurst: toBoolean(input.hasEliteHurst, SETTINGS_DEFAULTS.hasEliteHurst),
    hurstMeanRevertThreshold: toNumber(input.hurstMeanRevertThreshold, SETTINGS_DEFAULTS.hurstMeanRevertThreshold, { min: 0.0, max: 1.0, integer: false }),
    hurstTrendThreshold: toNumber(input.hurstTrendThreshold, SETTINGS_DEFAULTS.hurstTrendThreshold, { min: 0.0, max: 1.0, integer: false }),
    minAdaptiveExpiry: toNumber(input.minAdaptiveExpiry, SETTINGS_DEFAULTS.minAdaptiveExpiry, { min: 5, max: 3600, integer: true }),
    hurstMinScaleCutoff: toNumber(input.hurstMinScaleCutoff, SETTINGS_DEFAULTS.hurstMinScaleCutoff, { min: 4, max: 50, integer: true }),
    hurstAiConfidenceThreshold: toNumber(input.hurstAiConfidenceThreshold, SETTINGS_DEFAULTS.hurstAiConfidenceThreshold, { min: 50, max: 100, integer: true }),



    showGhostEntryMarkers: toBoolean(input.showGhostEntryMarkers, SETTINGS_DEFAULTS.showGhostEntryMarkers),
    showLiveEntryMarkers: toBoolean(input.showLiveEntryMarkers, SETTINGS_DEFAULTS.showLiveEntryMarkers),

    initialBalance: toNumber(input.initialBalance, SETTINGS_DEFAULTS.initialBalance, { min: 0, max: 100000000, integer: false }),
    payoutPercentage: toNumber(input.payoutPercentage, SETTINGS_DEFAULTS.payoutPercentage, { min: 0, max: 1000, integer: false }),
    riskPercentPerTrade: toNumber(input.riskPercentPerTrade, SETTINGS_DEFAULTS.riskPercentPerTrade, { min: 0, max: 100, integer: false }),
    drawdownPercent: toNumber(input.drawdownPercent, SETTINGS_DEFAULTS.drawdownPercent, { min: 0, max: 100, integer: false }),
    riskRewardRatio: toNumber(input.riskRewardRatio, SETTINGS_DEFAULTS.riskRewardRatio, { min: 0, max: 100, integer: false }),
    useFixedAmount: toBoolean(input.useFixedAmount, SETTINGS_DEFAULTS.useFixedAmount),
    fixedRiskAmount: toNumber(input.fixedRiskAmount, SETTINGS_DEFAULTS.fixedRiskAmount, { min: 0, max: 100000, integer: false }),
    tradesPerRun: toNumber(input.tradesPerRun, SETTINGS_DEFAULTS.tradesPerRun, { min: 1, max: 100, integer: true }),
    maxRuns: toNumber(input.maxRuns, SETTINGS_DEFAULTS.maxRuns, { min: 1, max: 100, integer: true }),

    maxDailyLoss: toNumber(input.maxDailyLoss, SETTINGS_DEFAULTS.maxDailyLoss, { min: 0, max: 100000, integer: false }),
    maxTradesPerSession: toNumber(input.maxTradesPerSession, SETTINGS_DEFAULTS.maxTradesPerSession, { min: 1, max: 1000, integer: true }),
    stopOnLossStreak: toNumber(input.stopOnLossStreak, SETTINGS_DEFAULTS.stopOnLossStreak, { min: 0, max: 100, integer: true }),

    aiModel: typeof input.aiModel === 'string' && input.aiModel.trim()
      ? input.aiModel.trim()
      : SETTINGS_DEFAULTS.aiModel,
    aiDevMode: toBoolean(input.aiDevMode, SETTINGS_DEFAULTS.aiDevMode),
    oteoAiExecutionMode: ['advisory', 'confirmation'].includes(input.oteoAiExecutionMode) ? input.oteoAiExecutionMode : 'advisory',
    aiTradeInterval: toNumber(input.aiTradeInterval, SETTINGS_DEFAULTS.aiTradeInterval, { min: 1, max: 100, integer: true }),
    aiPulseEnabled: toBoolean(input.aiPulseEnabled, SETTINGS_DEFAULTS.aiPulseEnabled),
    aiPulseIntervalSeconds: toNumber(input.aiPulseIntervalSeconds, SETTINGS_DEFAULTS.aiPulseIntervalSeconds, { min: 10, max: 3600, integer: true }),


    // AI Profiles (including Grok Native TTS voice settings)
    aiProfiles: input.aiProfiles && typeof input.aiProfiles === 'object' ? input.aiProfiles : null,
    activeAiProfile: typeof input.activeAiProfile === 'string' ? input.activeAiProfile : 'default',
    featureProfiles: input.featureProfiles && typeof input.featureProfiles === 'object'
      ? { ...SETTINGS_DEFAULTS.featureProfiles, ...input.featureProfiles }
      : { ...SETTINGS_DEFAULTS.featureProfiles },

    showManipulationAlerts: toBoolean(input.showManipulationAlerts, SETTINGS_DEFAULTS.showManipulationAlerts),
    showSignalConfidence: toBoolean(input.showSignalConfidence, SETTINGS_DEFAULTS.showSignalConfidence),
    autoFocusOnSignal: toBoolean(input.autoFocusOnSignal, SETTINGS_DEFAULTS.autoFocusOnSignal),

    assetAutoRefreshEnabled: toBoolean(input.assetAutoRefreshEnabled, SETTINGS_DEFAULTS.assetAutoRefreshEnabled),
    assetAutoRefreshInterval: toNumber(input.assetAutoRefreshInterval, SETTINGS_DEFAULTS.assetAutoRefreshInterval, { min: 10, max: 3600, integer: true }),

    miniChartConfig: {
      showSparkline: toBoolean(input.miniChartConfig?.showSparkline, SETTINGS_DEFAULTS.miniChartConfig.showSparkline),
      showGauge: toBoolean(input.miniChartConfig?.showGauge, SETTINGS_DEFAULTS.miniChartConfig.showGauge),
      gaugeOnHover: toBoolean(input.miniChartConfig?.gaugeOnHover, SETTINGS_DEFAULTS.miniChartConfig.gaugeOnHover),
      showStats: toBoolean(input.miniChartConfig?.showStats, SETTINGS_DEFAULTS.miniChartConfig.showStats),
      showRegime: toBoolean(input.miniChartConfig?.showRegime, SETTINGS_DEFAULTS.miniChartConfig.showRegime),
      showManipulation: toBoolean(input.miniChartConfig?.showManipulation, SETTINGS_DEFAULTS.miniChartConfig.showManipulation),
    },
    uiSoundsEnabled: toBoolean(input.uiSoundsEnabled, SETTINGS_DEFAULTS.uiSoundsEnabled),
    tradingSoundsEnabled: toBoolean(input.tradingSoundsEnabled, SETTINGS_DEFAULTS.tradingSoundsEnabled),
    notificationSoundsEnabled: toBoolean(input.notificationSoundsEnabled, SETTINGS_DEFAULTS.notificationSoundsEnabled),
    dontDisturbEnabled: toBoolean(input.dontDisturbEnabled, SETTINGS_DEFAULTS.dontDisturbEnabled),
    showGlobalTimer: toBoolean(input.showGlobalTimer, SETTINGS_DEFAULTS.showGlobalTimer),
  };
}

function commitSettingsPatch(set, patch) {
  set((state) => ({
    ...state,
    ...validateSettings({ ...state, ...patch }),
  }));
}

export const useSettingsStore = create()(
  persist(
    (set) => ({
      ...SETTINGS_DEFAULTS,

      updateSettings: (patch) => commitSettingsPatch(set, patch),
      resetSettings: () => set({ ...SETTINGS_DEFAULTS }),

      setOteoEnabled: (val) => commitSettingsPatch(set, { oteoEnabled: val }),
      setOteoLevel2Enabled: (val) =>
        set((state) => ({
          ...state,
          ...validateSettings({
            ...state,
            oteoLevel2Enabled: val,
            oteoLevel3Enabled: val ? state.oteoLevel3Enabled : false,
          }),
        })),
      setOteoLevel3Enabled: (val) =>
        set((state) => ({
          ...state,
          ...validateSettings({
            ...state,
            oteoLevel2Enabled: val ? true : state.oteoLevel2Enabled,
            oteoLevel3Enabled: val,
          }),
        })),
      setOteoAiEnabled: (val) => commitSettingsPatch(set, { oteoAiEnabled: val }),
      setOteoWarmupBars: (val) => commitSettingsPatch(set, { oteoWarmupBars: val }),
      setOteoCooldownBars: (val) => commitSettingsPatch(set, { oteoCooldownBars: val }),
      setGhostAmount: (val) => commitSettingsPatch(set, { ghostAmount: val }),
      setAutoGhostEnabled: (val) => commitSettingsPatch(set, { autoGhostEnabled: val }),
      setAutoGhostCopyMode: (val) => commitSettingsPatch(set, { autoGhostCopyMode: val }),
      setAutoGhostExpirationSeconds: (val) => commitSettingsPatch(set, { autoGhostExpirationSeconds: val }),
      setAutoGhostMaxConcurrentTrades: (val) => commitSettingsPatch(set, { autoGhostMaxConcurrentTrades: val }),
      setAutoGhostPerAssetCooldownSeconds: (val) => commitSettingsPatch(set, { autoGhostPerAssetCooldownSeconds: val }),
      setAutoGhostMaxSessionTrades: (val) => commitSettingsPatch(set, { autoGhostMaxSessionTrades: val }),
      setAutoGhostMaxDrawdownAmount: (val) => commitSettingsPatch(set, { autoGhostMaxDrawdownAmount: val }),
      setAutoGhostDrawdownCooldownSeconds: (val) => commitSettingsPatch(set, { autoGhostDrawdownCooldownSeconds: val }),
      setAutoGhostMinimumPayout: (val) => commitSettingsPatch(set, { autoGhostMinimumPayout: val }),
      setAutoGhostManipulationSeverityThreshold: (val) => commitSettingsPatch(set, { autoGhostManipulationSeverityThreshold: val }),
      setAutoGhostBlockOnManipulation: (val) => commitSettingsPatch(set, { autoGhostBlockOnManipulation: val }),
      setGhostWidgetPosition: (val) => commitSettingsPatch(set, { ghostWidgetPosition: val }),
      setGhostIcon: (val) => commitSettingsPatch(set, { ghostIcon: val }),
      setGhostMaxTradesPerTimeframe: (val) => commitSettingsPatch(set, { ghostMaxTradesPerTimeframe: val }),
      setGhostTimeframeSeconds: (val) => commitSettingsPatch(set, { ghostTimeframeSeconds: val }),
      setGhostMinConfidence: (val) => commitSettingsPatch(set, { ghostMinConfidence: val }),
      setGhostMinConfidenceEnabled: (val) => commitSettingsPatch(set, { ghostMinConfidenceEnabled: val }),
      setGhostMaxConfidence: (val) => commitSettingsPatch(set, { ghostMaxConfidence: val }),
      setGhostMaxConfidenceEnabled: (val) => commitSettingsPatch(set, { ghostMaxConfidenceEnabled: val }),
      setGhostMinZScore: (val) => commitSettingsPatch(set, { ghostMinZScore: val }),
      setGhostMinZScoreEnabled: (val) => commitSettingsPatch(set, { ghostMinZScoreEnabled: val }),
      setGhostMaxZScore: (val) => commitSettingsPatch(set, { ghostMaxZScore: val }),
      setGhostMaxZScoreEnabled: (val) => commitSettingsPatch(set, { ghostMaxZScoreEnabled: val }),
      setGhostRegimeGateEnabled: (val) => commitSettingsPatch(set, { ghostRegimeGateEnabled: val }),
      setGhostAllowedRegimes: (val) => commitSettingsPatch(set, { ghostAllowedRegimes: val }),
      setGhostRequireRegimeStable: (val) => commitSettingsPatch(set, { ghostRequireRegimeStable: val }),
      setGhostProtocols: (val) => commitSettingsPatch(set, { ghostProtocols: val }),
      setActiveGhostProtocol: (val) => commitSettingsPatch(set, { activeGhostProtocol: val }),

      setHurstFilterEnabled: (val) => commitSettingsPatch(set, { hurstFilterEnabled: val }),
      setHurstFilterThreshold: (val) => commitSettingsPatch(set, { hurstFilterThreshold: val }),
      setHasPremiumHurst: (val) => commitSettingsPatch(set, { hasPremiumHurst: val }),
      setHasEliteHurst: (val) => commitSettingsPatch(set, { hasEliteHurst: val }),
      setHurstMeanRevertThreshold: (val) => commitSettingsPatch(set, { hurstMeanRevertThreshold: val }),
      setHurstTrendThreshold: (val) => commitSettingsPatch(set, { hurstTrendThreshold: val }),
      setMinAdaptiveExpiry: (val) => commitSettingsPatch(set, { minAdaptiveExpiry: val }),
      setHurstMinScaleCutoff: (val) => commitSettingsPatch(set, { hurstMinScaleCutoff: val }),
      setHurstAiConfidenceThreshold: (val) => commitSettingsPatch(set, { hurstAiConfidenceThreshold: val }),
      loadGhostProtocol: (key) => {
        set((state) => {
          const protocols = state.ghostProtocols || {};
          const proto = protocols[key];
          if (!proto) {
            if (key === 'default') {
              return {
                ...state,
                ...validateSettings({
                  ...state,
                  activeGhostProtocol: 'default',
                  ghostMinZScoreEnabled: false,
                  ghostMaxZScoreEnabled: false,
                  ghostRegimeGateEnabled: false,
                  ghostAllowedRegimes: [],
                  ghostRequireRegimeStable: false,
                })
              };
            }
            return state;
          }
          const gates = proto.gates || {};
          return {
            ...state,
            ...validateSettings({
              ...state,
              activeGhostProtocol: key,
              ghostMinZScoreEnabled: gates.minZScoreEnabled ?? false,
              ghostMinZScore: gates.minZScore ?? -0.5,
              ghostMaxZScoreEnabled: gates.maxZScoreEnabled ?? false,
              ghostMaxZScore: gates.maxZScore ?? 1.5,
              ghostRegimeGateEnabled: gates.regimeGateEnabled ?? false,
              ghostAllowedRegimes: gates.allowedRegimes ?? [],
              ghostRequireRegimeStable: gates.requireRegimeStable ?? false,
            })
          };
        });
      },

      setShowGhostEntryMarkers: (val) => commitSettingsPatch(set, { showGhostEntryMarkers: val }),
      setShowLiveEntryMarkers: (val) => commitSettingsPatch(set, { showLiveEntryMarkers: val }),
      setInitialBalance: (val) => commitSettingsPatch(set, { initialBalance: val }),
      setPayoutPercentage: (val) => commitSettingsPatch(set, { payoutPercentage: val }),
      setRiskPercentPerTrade: (val) => commitSettingsPatch(set, { riskPercentPerTrade: val }),
      setDrawdownPercent: (val) => commitSettingsPatch(set, { drawdownPercent: val }),
      setRiskRewardRatio: (val) => commitSettingsPatch(set, { riskRewardRatio: val }),
      setUseFixedAmount: (val) => commitSettingsPatch(set, { useFixedAmount: val }),
      setFixedRiskAmount: (val) => commitSettingsPatch(set, { fixedRiskAmount: val }),
      setTradesPerRun: (val) => commitSettingsPatch(set, { tradesPerRun: val }),
      setMaxRuns: (val) => commitSettingsPatch(set, { maxRuns: val }),
      setMaxDailyLoss: (val) => commitSettingsPatch(set, { maxDailyLoss: val }),
      setMaxTradesPerSession: (val) => commitSettingsPatch(set, { maxTradesPerSession: val }),
      setStopOnLossStreak: (val) => commitSettingsPatch(set, { stopOnLossStreak: val }),
      setAiModel: (val) => commitSettingsPatch(set, { aiModel: val }),
      setAiDevMode: (val) => commitSettingsPatch(set, { aiDevMode: val }),
      setOteoAiExecutionMode: (val) => commitSettingsPatch(set, { oteoAiExecutionMode: val }),
      setAiTradeInterval: (val) => commitSettingsPatch(set, { aiTradeInterval: val }),
      setAiPulseEnabled: (val) => commitSettingsPatch(set, { aiPulseEnabled: val }),
      setAiPulseIntervalSeconds: (val) => commitSettingsPatch(set, { aiPulseIntervalSeconds: val }),


      // Rich AI profiles management (dedicated AI Settings)
      setAiProfiles: (profiles) => commitSettingsPatch(set, { aiProfiles: profiles }),
      setActiveAiProfile: (key) => commitSettingsPatch(set, { activeAiProfile: key }),
      setFeatureProfile: (feature, profileKey) => set((state) => ({
        featureProfiles: { ...state.featureProfiles, [feature]: profileKey },
      })),
      setShowManipulationAlerts: (val) => commitSettingsPatch(set, { showManipulationAlerts: val }),
      setShowSignalConfidence: (val) => commitSettingsPatch(set, { showSignalConfidence: val }),
      setAutoFocusOnSignal: (val) => commitSettingsPatch(set, { autoFocusOnSignal: val }),
      setAssetAutoRefreshEnabled: (val) => commitSettingsPatch(set, { assetAutoRefreshEnabled: val }),
      setAssetAutoRefreshInterval: (val) => commitSettingsPatch(set, { assetAutoRefreshInterval: val }),
      setMiniChartConfig: (patch) => set((state) => ({
        miniChartConfig: { ...state.miniChartConfig, ...patch }
      })),
      setUiSoundsEnabled: (val) => commitSettingsPatch(set, { uiSoundsEnabled: val }),
      setTradingSoundsEnabled: (val) => commitSettingsPatch(set, { tradingSoundsEnabled: val }),
      setNotificationSoundsEnabled: (val) => commitSettingsPatch(set, { notificationSoundsEnabled: val }),
      setDontDisturbEnabled: (val) => commitSettingsPatch(set, { dontDisturbEnabled: val }),
      setShowGlobalTimer: (val) => commitSettingsPatch(set, { showGlobalTimer: val }),
    }),
    {
      name: 'otc-sniper-settings-storage',
      partialize: (state) => validateSettings(state),
    }
  )
);
