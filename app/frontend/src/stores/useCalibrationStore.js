/**
 * Live Calibration Mode status — NOT persisted.
 * Backend CalibrationService is the owner; this store only observes.
 */
import { create } from 'zustand';

const LOCKED_STATES = new Set(['RUNNING', 'ANALYZING', 'PROPOSING']);

export const CALIBRATION_DEFAULT_STATUS = {
  state: 'IDLE',
  calibrationId: null,
  startedAt: 0,
  elapsedSeconds: 0,
  timeBudgetSeconds: 25 * 60,
  tradeBudget: 24,
  settledWins: 0,
  settledLosses: 0,
  settledVoids: 0,
  settledTotal: 0,
  calibrationPnl: 0,
  autonomyTier: 'tiered',
  locked: false,
  stopRequested: false,
  stopReason: null,
  strictnessPresets: null,
};

export function isCalibrationLockedState(state) {
  return LOCKED_STATES.has(String(state || '').toUpperCase());
}

export function isCalibrationSessionId(sessionId) {
  return typeof sessionId === 'string' && sessionId.startsWith('auto_ghost_calib_');
}

export const useCalibrationStore = create((set) => ({
  ...CALIBRATION_DEFAULT_STATUS,

  applyStatus: (payload) => {
    if (!payload || typeof payload !== 'object') return;
    const state = payload.state || 'IDLE';
    set({
      state,
      calibrationId: payload.calibration_id ?? null,
      startedAt: Number(payload.started_at) || 0,
      elapsedSeconds: Number(payload.elapsed_seconds) || 0,
      timeBudgetSeconds: Number(payload.time_budget_seconds) || 25 * 60,
      tradeBudget: Number(payload.trade_budget) || 24,
      settledWins: Number(payload.settled_wins) || 0,
      settledLosses: Number(payload.settled_losses) || 0,
      settledVoids: Number(payload.settled_voids) || 0,
      settledTotal: Number(payload.settled_total) || 0,
      calibrationPnl: Number(payload.calibration_pnl) || 0,
      autonomyTier: payload.autonomy_tier || 'tiered',
      locked: payload.locked != null ? Boolean(payload.locked) : isCalibrationLockedState(state),
      stopRequested: Boolean(payload.stop_requested),
      stopReason: payload.stop_reason ?? null,
    });
  },

  setStrictnessPresets: (presets) => set({ strictnessPresets: presets || null }),

  reset: () => set({ ...CALIBRATION_DEFAULT_STATUS }),
}));
