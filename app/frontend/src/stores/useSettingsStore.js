/**
 * Settings store — app-level configuration (not account/session).
 * Persisted to localStorage.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useSettingsStore = create()(
  persist(
    (set) => ({
      // OTEO configuration
      oteoEnabled: true,
      oteoWarmupBars: 20,
      oteoCooldownBars: 3,

      // Ghost trading
      ghostTradingEnabled: false,
      ghostAmount: 1,

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

      // UI preferences
      showManipulationAlerts: true,
      showSignalConfidence: true,
      autoFocusOnSignal: false,

      setOteoEnabled: (val) => set({ oteoEnabled: val }),
      setOteoWarmupBars: (val) => set({ oteoWarmupBars: val }),
      setOteoCooldownBars: (val) => set({ oteoCooldownBars: val }),
      setGhostTradingEnabled: (val) => set({ ghostTradingEnabled: val }),
      setGhostAmount: (val) => set({ ghostAmount: val }),
      setInitialBalance: (val) => set({ initialBalance: val }),
      setPayoutPercentage: (val) => set({ payoutPercentage: val }),
      setRiskPercentPerTrade: (val) => set({ riskPercentPerTrade: val }),
      setDrawdownPercent: (val) => set({ drawdownPercent: val }),
      setRiskRewardRatio: (val) => set({ riskRewardRatio: val }),
      setUseFixedAmount: (val) => set({ useFixedAmount: val }),
      setFixedRiskAmount: (val) => set({ fixedRiskAmount: val }),
      setTradesPerRun: (val) => set({ tradesPerRun: val }),
      setMaxRuns: (val) => set({ maxRuns: val }),
      setMaxDailyLoss: (val) => set({ maxDailyLoss: val }),
      setMaxTradesPerSession: (val) => set({ maxTradesPerSession: val }),
      setStopOnLossStreak: (val) => set({ stopOnLossStreak: val }),
      setShowManipulationAlerts: (val) => set({ showManipulationAlerts: val }),
      setShowSignalConfidence: (val) => set({ showSignalConfidence: val }),
      setAutoFocusOnSignal: (val) => set({ autoFocusOnSignal: val }),
    }),
    { name: 'otc-sniper-settings-storage' }
  )
);
