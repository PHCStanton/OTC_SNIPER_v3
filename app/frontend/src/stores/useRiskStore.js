/**
 * Risk store — session P/L, win rate, streak tracking.
 * Updated from trade results and session data.
 */
import { create } from 'zustand';

export const useRiskStore = create((set, get) => ({
  // Session stats
  sessionPnl: 0,
  sessionWins: 0,
  sessionLosses: 0,
  currentStreak: 0,   // positive = win streak, negative = loss streak
  peakBalance: 0,
  startBalance: 0,

  // Derived (computed on update)
  winRate: 0,
  totalTrades: 0,
  maxDrawdown: 0,

  setStartBalance: (balance) =>
    set({ startBalance: balance, peakBalance: balance }),

  recordTradeResult: (outcome, pnl) => {
    const state = get();
    const isWin = outcome === 'win';
    const sessionWins = state.sessionWins + (isWin ? 1 : 0);
    const sessionLosses = state.sessionLosses + (isWin ? 0 : 1);
    const totalTrades = sessionWins + sessionLosses;
    const sessionPnl = state.sessionPnl + pnl;
    const winRate = totalTrades > 0 ? (sessionWins / totalTrades) * 100 : 0;

    // Streak: positive = consecutive wins, negative = consecutive losses
    let currentStreak = state.currentStreak;
    if (isWin) {
      currentStreak = currentStreak >= 0 ? currentStreak + 1 : 1;
    } else {
      currentStreak = currentStreak <= 0 ? currentStreak - 1 : -1;
    }

    const peakBalance = Math.max(state.peakBalance, state.startBalance + sessionPnl);
    const maxDrawdown = Math.max(
      state.maxDrawdown,
      peakBalance - (state.startBalance + sessionPnl)
    );

    set({
      sessionPnl,
      sessionWins,
      sessionLosses,
      totalTrades,
      winRate,
      currentStreak,
      peakBalance,
      maxDrawdown,
    });
  },

  resetSession: () =>
    set({
      sessionPnl: 0,
      sessionWins: 0,
      sessionLosses: 0,
      currentStreak: 0,
      peakBalance: 0,
      startBalance: 0,
      winRate: 0,
      totalTrades: 0,
      maxDrawdown: 0,
    }),
}));
