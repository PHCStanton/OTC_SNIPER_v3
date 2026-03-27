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
