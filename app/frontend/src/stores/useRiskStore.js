/**
 * Risk store — session P/L, win rate, streak tracking, trade runs, and manual overrides.
 */
import { create } from 'zustand';
import { useSettingsStore } from './useSettingsStore.js';

const VALID_OUTCOMES = new Set(['win', 'loss', 'void']);

function createRun(runNumber) {
  return {
    id: runNumber,
    label: `Trade Run ${runNumber}`,
    trades: [],
    pnl: 0,
    createdAt: new Date().toISOString(),
    completedAt: null,
  };
}

function createTrade({ outcome, pnl, stake, payoutPercentage, source }) {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    outcome,
    pnl,
    stake,
    payoutPercentage,
    source,
    edited: false,
    createdAt: new Date().toISOString(),
  };
}

function normalizeNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function applyOutcome(trade, nextOutcome) {
  const outcome = nextOutcome.toLowerCase();
  const stake = normalizeNumber(trade.stake, 0);
  const payoutPercentage = normalizeNumber(trade.payoutPercentage, 0);

  if (outcome === 'win') {
    return { ...trade, outcome, pnl: stake * (payoutPercentage / 100), edited: true };
  }

  if (outcome === 'loss') {
    return { ...trade, outcome, pnl: -stake, edited: true };
  }

  return { ...trade, outcome: 'void', pnl: 0, edited: true };
}

function summarizeSession(startBalance, tradeRuns, currentTradeRun) {
  const completedRuns = tradeRuns.map((run) => {
    let runPnl = 0;
    let wins = 0;
    let losses = 0;
    let voids = 0;

    const trades = run.trades.map((trade) => {
      const normalized = {
        ...trade,
        outcome: VALID_OUTCOMES.has(trade.outcome) ? trade.outcome : 'void',
        pnl: normalizeNumber(trade.pnl, 0),
        stake: normalizeNumber(trade.stake, 0),
        payoutPercentage: normalizeNumber(trade.payoutPercentage, 0),
      };

      runPnl += normalized.pnl;
      if (normalized.outcome === 'win') wins += 1;
      if (normalized.outcome === 'loss') losses += 1;
      if (normalized.outcome === 'void') voids += 1;

      return normalized;
    });

    return {
      ...run,
      trades,
      pnl: runPnl,
      wins,
      losses,
      voids,
      totalTrades: trades.length,
      resolvedTrades: wins + losses,
    };
  });

  const currentRunTrades = currentTradeRun.trades.map((trade) => ({
    ...trade,
    outcome: VALID_OUTCOMES.has(trade.outcome) ? trade.outcome : 'void',
    pnl: normalizeNumber(trade.pnl, 0),
    stake: normalizeNumber(trade.stake, 0),
    payoutPercentage: normalizeNumber(trade.payoutPercentage, 0),
  }));

  const currentRun = {
    ...currentTradeRun,
    trades: currentRunTrades,
    pnl: currentRunTrades.reduce((sum, trade) => sum + trade.pnl, 0),
    wins: currentRunTrades.filter((trade) => trade.outcome === 'win').length,
    losses: currentRunTrades.filter((trade) => trade.outcome === 'loss').length,
    voids: currentRunTrades.filter((trade) => trade.outcome === 'void').length,
    totalTrades: currentRunTrades.length,
    resolvedTrades: currentRunTrades.filter((trade) => trade.outcome === 'win' || trade.outcome === 'loss').length,
  };

  const orderedTrades = [...completedRuns, currentRun].flatMap((run) => run.trades);

  let sessionWins = 0;
  let sessionLosses = 0;
  let sessionVoids = 0;
  let resolvedTrades = 0;
  let totalTrades = 0;
  let sessionPnl = 0;
  let currentStreak = 0;
  let peakBalance = startBalance;
  let maxDrawdown = 0;

  orderedTrades.forEach((trade) => {
    const nextPnl = normalizeNumber(trade.pnl, 0);
    sessionPnl += nextPnl;
    totalTrades += 1;

    if (trade.outcome === 'win') {
      sessionWins += 1;
      resolvedTrades += 1;
      currentStreak = currentStreak >= 0 ? currentStreak + 1 : 1;
    } else if (trade.outcome === 'loss') {
      sessionLosses += 1;
      resolvedTrades += 1;
      currentStreak = currentStreak <= 0 ? currentStreak - 1 : -1;
    } else {
      sessionVoids += 1;
    }

    const currentBalance = startBalance + sessionPnl;
    peakBalance = Math.max(peakBalance, currentBalance);
    maxDrawdown = Math.max(maxDrawdown, peakBalance - currentBalance);
  });

  const currentBalance = startBalance + sessionPnl;
  const winRate = resolvedTrades > 0 ? (sessionWins / resolvedTrades) * 100 : 0;

  return {
    tradeRuns: completedRuns,
    currentTradeRun: currentRun,
    sessionWins,
    sessionLosses,
    sessionVoids,
    resolvedTrades,
    totalTrades,
    sessionPnl,
    currentBalance,
    currentStreak,
    peakBalance,
    maxDrawdown,
    winRate,
  };
}

function summarizeGhostTrades(ghostTrades) {
  const trades = ghostTrades.map((trade) => ({
    ...trade,
    outcome: VALID_OUTCOMES.has(trade.outcome) ? trade.outcome : 'void',
    pnl: normalizeNumber(trade.pnl, 0),
    stake: normalizeNumber(trade.stake, 0),
  }));

  let wins = 0;
  let losses = 0;
  let resolvedTrades = 0;
  let pnl = 0;
  let peak = 0;
  let running = 0;
  let maxDrawdown = 0;

  trades.forEach((trade) => {
    pnl += trade.pnl;
    running += trade.pnl;
    peak = Math.max(peak, running);
    maxDrawdown = Math.max(maxDrawdown, peak - running);
    if (trade.outcome === 'win') {
      wins += 1;
      resolvedTrades += 1;
    } else if (trade.outcome === 'loss') {
      losses += 1;
      resolvedTrades += 1;
    }
  });

  return {
    ghostTrades: trades,
    ghostWins: wins,
    ghostLosses: losses,
    ghostPnl: pnl,
    ghostTotalTrades: trades.length,
    ghostWinRate: resolvedTrades > 0 ? (wins / resolvedTrades) * 100 : 0,
    ghostMaxDrawdown: maxDrawdown,
  };
}

export const useRiskStore = create((set, get) => ({
  // Session configuration
  startBalance: 0,
  recordingMode: 'auto', // 'auto' | 'manual'

  // Session stats
  sessionPnl: 0,
  sessionWins: 0,
  sessionLosses: 0,
  sessionVoids: 0,
  resolvedTrades: 0,
  currentBalance: 0,
  currentStreak: 0,   // positive = win streak, negative = loss streak
  peakBalance: 0,

  // Derived (computed on update)
  winRate: 0,
  totalTrades: 0,
  maxDrawdown: 0,

  // Trade run history
  tradeRuns: [],
  currentTradeRun: createRun(1),
  ghostTrades: [],
  ghostPnl: 0,
  ghostWins: 0,
  ghostLosses: 0,
  ghostTotalTrades: 0,
  ghostWinRate: 0,
  ghostMaxDrawdown: 0,

  setRecordingMode: (mode) => {
    if (!['auto', 'manual'].includes(mode)) {
      throw new Error(`Invalid recording mode: ${mode}`);
    }
    set({ recordingMode: mode });
  },

  /**
   * syncStartBalance — sets the session starting balance from a live account balance.
   * IMPORTANT: This is intended for initial session sync only (when startBalance === 0).
   * Calling it mid-session will back-calculate startBalance from the current sessionPnl,
   * which may produce unexpected results if trades have already been recorded.
   * The SessionRiskPanel useEffect guards this by only calling when startBalance === 0.
   */
  syncStartBalance: (balance) => {
    const nextBalance = normalizeNumber(balance, 0);
    set((state) => {
      const startBalance = Math.max(0, nextBalance - state.sessionPnl);
      return {
        startBalance,
        peakBalance: Math.max(state.peakBalance, nextBalance),
        ...summarizeSession(startBalance, state.tradeRuns, state.currentTradeRun),
      };
    });
  },

  recordTradeResult: ({ outcome, pnl, stake, payoutPercentage, source = 'auto' }) => {
    const state = get();

    if (!VALID_OUTCOMES.has(outcome)) {
      throw new Error(`Invalid trade outcome: ${outcome}`);
    }

    const settings = useSettingsStore.getState();
    const resolvedPayout = normalizeNumber(payoutPercentage, settings.payoutPercentage);
    const resolvedStake = normalizeNumber(
      stake,
      settings.useFixedAmount ? settings.fixedRiskAmount : state.startBalance * (settings.riskPercentPerTrade / 100)
    );
    const resolvedPnl = normalizeNumber(pnl, 0);

    const activeRun = state.currentTradeRun.trades.length > 0
      ? state.currentTradeRun
      : createRun(state.tradeRuns.length + 1);

    const nextTrade = createTrade({
      outcome,
      pnl: outcome === 'void' ? 0 : resolvedPnl,
      stake: resolvedStake,
      payoutPercentage: resolvedPayout,
      source,
    });

    if (source === 'ghost') {
      set({
        ...summarizeGhostTrades([...state.ghostTrades, nextTrade]),
      });
      return;
    }

    const nextCurrentTradeRun = {
      ...activeRun,
      trades: [...activeRun.trades, nextTrade],
    };

    const tradesPerRun = Math.max(1, normalizeNumber(settings.tradesPerRun, 4));

    if (nextCurrentTradeRun.trades.length >= tradesPerRun) {
      const completedRun = {
        ...nextCurrentTradeRun,
        completedAt: new Date().toISOString(),
      };

      const nextTradeRuns = [...state.tradeRuns, completedRun];
      const nextCurrentRun = createRun(nextTradeRuns.length + 1);

      set({
        ...summarizeSession(state.startBalance, nextTradeRuns, nextCurrentRun),
      });
      return;
    }

    set({
      ...summarizeSession(state.startBalance, state.tradeRuns, nextCurrentTradeRun),
    });
  },

  /**
   * startNewTradeRun — seals the active Trade Run and opens a new one.
   * Intended for manual "New Trade Run" button use only.
   * No-op if the current run has no trades.
   */
  startNewTradeRun: () => {
    const state = get();
    if (state.currentTradeRun.trades.length === 0) {
      return;
    }

    const completedRun = {
      ...state.currentTradeRun,
      completedAt: new Date().toISOString(),
    };

    const nextTradeRuns = [...state.tradeRuns, completedRun];
    const nextCurrentRun = createRun(nextTradeRuns.length + 1);

    set({
      ...summarizeSession(state.startBalance, nextTradeRuns, nextCurrentRun),
    });
  },

  overrideTradeResult: (runId, tradeId, nextOutcome) => {
    if (!VALID_OUTCOMES.has(nextOutcome)) {
      throw new Error(`Invalid override outcome: ${nextOutcome}`);
    }

    const state = get();
    const updateRun = (run) => {
      if (String(run.id) !== String(runId)) {
        return run;
      }

      const updatedTrades = run.trades.map((trade) => {
        if (String(trade.id) !== String(tradeId)) {
          return trade;
        }

        return applyOutcome(trade, nextOutcome);
      });

      return {
        ...run,
        trades: updatedTrades,
        completedAt: run.completedAt ?? null,
      };
    };

    const nextTradeRuns = state.tradeRuns.map(updateRun);
    const nextCurrentTradeRun = String(state.currentTradeRun.id) === String(runId)
      ? updateRun(state.currentTradeRun)
      : state.currentTradeRun;

    set({
      ...summarizeSession(state.startBalance, nextTradeRuns, nextCurrentTradeRun),
    });
  },

  resetSession: () =>
    set({
      startBalance: 0,
      recordingMode: 'auto',
      sessionPnl: 0,
      sessionWins: 0,
      sessionLosses: 0,
      sessionVoids: 0,
      resolvedTrades: 0,
      currentBalance: 0,
      currentStreak: 0,
      peakBalance: 0,
      winRate: 0,
      totalTrades: 0,
      maxDrawdown: 0,
      tradeRuns: [],
      currentTradeRun: createRun(1),
      ghostTrades: [],
      ghostPnl: 0,
      ghostWins: 0,
      ghostLosses: 0,
      ghostTotalTrades: 0,
      ghostWinRate: 0,
      ghostMaxDrawdown: 0,
    }),
}));
