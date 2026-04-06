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
  oteoWarmupBars: 20,
  oteoCooldownBars: 3,

  // Ghost trading
  ghostTradingEnabled: false,
  ghostAmount: 1,
  autoGhostEnabled: false,
  autoGhostExpirationSeconds: 60,
  autoGhostMaxConcurrentTrades: 3,
  autoGhostPerAssetCooldownSeconds: 30,
  ghostWidgetPosition: { x: 0, y: 0 },
  ghostIcon: 'drift.gif',

  // Session risk defaults
  initialBalance: 1000,
  payoutPercentage: 80,
  riskPercentPerTrade: 1,
  drawdownPercent: 10,
  riskRewardRatio: 2,
  useFixedAmount: false,
  fixedRiskAmount: 10,
  tradesPerRun: 4,
  maxRuns: 3,

  // Risk management
  maxDailyLoss: 50,
  maxTradesPerSession: 20,
  stopOnLossStreak: 3,

  // AI integration
  aiModel: 'grok-4-1-fast-non-reasoning',

  // UI preferences
  showManipulationAlerts: true,
  showSignalConfidence: true,
  autoFocusOnSignal: false,
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
    oteoWarmupBars: toNumber(input.oteoWarmupBars, SETTINGS_DEFAULTS.oteoWarmupBars, { min: 0, max: 500, integer: true }),
    oteoCooldownBars: toNumber(input.oteoCooldownBars, SETTINGS_DEFAULTS.oteoCooldownBars, { min: 0, max: 500, integer: true }),

    ghostTradingEnabled: toBoolean(input.ghostTradingEnabled, SETTINGS_DEFAULTS.ghostTradingEnabled),
    ghostAmount: toNumber(input.ghostAmount, SETTINGS_DEFAULTS.ghostAmount, { min: 0, max: 100000, integer: false }),
    autoGhostEnabled: toBoolean(input.autoGhostEnabled, SETTINGS_DEFAULTS.autoGhostEnabled),
    autoGhostExpirationSeconds: toNumber(input.autoGhostExpirationSeconds, SETTINGS_DEFAULTS.autoGhostExpirationSeconds, { min: 5, max: 3600, integer: true }),
    autoGhostMaxConcurrentTrades: toNumber(input.autoGhostMaxConcurrentTrades, SETTINGS_DEFAULTS.autoGhostMaxConcurrentTrades, { min: 1, max: 20, integer: true }),
    autoGhostPerAssetCooldownSeconds: toNumber(input.autoGhostPerAssetCooldownSeconds, SETTINGS_DEFAULTS.autoGhostPerAssetCooldownSeconds, { min: 0, max: 3600, integer: true }),
    ghostWidgetPosition: toPosition(input.ghostWidgetPosition, SETTINGS_DEFAULTS.ghostWidgetPosition),
    ghostIcon: typeof input.ghostIcon === 'string' && input.ghostIcon.trim()
      ? input.ghostIcon.trim()
      : SETTINGS_DEFAULTS.ghostIcon,

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

    showManipulationAlerts: toBoolean(input.showManipulationAlerts, SETTINGS_DEFAULTS.showManipulationAlerts),
    showSignalConfidence: toBoolean(input.showSignalConfidence, SETTINGS_DEFAULTS.showSignalConfidence),
    autoFocusOnSignal: toBoolean(input.autoFocusOnSignal, SETTINGS_DEFAULTS.autoFocusOnSignal),
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
      setOteoWarmupBars: (val) => commitSettingsPatch(set, { oteoWarmupBars: val }),
      setOteoCooldownBars: (val) => commitSettingsPatch(set, { oteoCooldownBars: val }),
      setGhostTradingEnabled: (val) => commitSettingsPatch(set, { ghostTradingEnabled: val }),
      setGhostAmount: (val) => commitSettingsPatch(set, { ghostAmount: val }),
      setAutoGhostEnabled: (val) => commitSettingsPatch(set, { autoGhostEnabled: val }),
      setAutoGhostExpirationSeconds: (val) => commitSettingsPatch(set, { autoGhostExpirationSeconds: val }),
      setAutoGhostMaxConcurrentTrades: (val) => commitSettingsPatch(set, { autoGhostMaxConcurrentTrades: val }),
      setAutoGhostPerAssetCooldownSeconds: (val) => commitSettingsPatch(set, { autoGhostPerAssetCooldownSeconds: val }),
      setGhostWidgetPosition: (val) => commitSettingsPatch(set, { ghostWidgetPosition: val }),
      setGhostIcon: (val) => commitSettingsPatch(set, { ghostIcon: val }),
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
      setShowManipulationAlerts: (val) => commitSettingsPatch(set, { showManipulationAlerts: val }),
      setShowSignalConfidence: (val) => commitSettingsPatch(set, { showSignalConfidence: val }),
      setAutoFocusOnSignal: (val) => commitSettingsPatch(set, { autoFocusOnSignal: val }),
    }),
    {
      name: 'otc-sniper-settings-storage',
      partialize: (state) => validateSettings(state),
    }
  )
);
