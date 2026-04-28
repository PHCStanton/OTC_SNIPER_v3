import React from 'react';
import { TrendingUp } from 'lucide-react';

export default function StreakAnalytics({ autoGhostMetrics }) {
  // Use real backend data if available, fallback to empty stats
  const maxWinStreak = autoGhostMetrics?.auto_ghost_max_win_streak || 0;
  const maxLossStreak = autoGhostMetrics?.auto_ghost_max_loss_streak || 0;
  const currentStreak = autoGhostMetrics?.auto_ghost_current_streak_count || 0;
  const currentType = autoGhostMetrics?.auto_ghost_current_streak_type || null;

  return (
    <div className="bg-[#141818] border border-white/5 rounded-xl p-5">
      <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2 uppercase tracking-wider">
        <TrendingUp size={16} className="text-[#f5df19]" />
        Streak Distribution
      </h3>
      <div className="flex flex-col gap-6">
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-center">
            <p className="text-[10px] text-emerald-500/70 font-bold uppercase tracking-wider">Max Win Streak</p>
            <p className="text-2xl font-black text-emerald-400 mt-1">{maxWinStreak}</p>
          </div>
          <div className="bg-rose-500/10 border border-rose-500/20 rounded-lg p-3 text-center">
            <p className="text-[10px] text-rose-500/70 font-bold uppercase tracking-wider">Max Loss Streak</p>
            <p className="text-2xl font-black text-rose-400 mt-1">{maxLossStreak}</p>
          </div>
        </div>
        
        <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/10">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Current Active Streak</span>
          {currentType ? (
            <span className={`text-sm font-black px-2 py-0.5 rounded-full ${
              currentType === 'win' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
            }`}>
              {currentStreak} {currentType.toUpperCase()}
            </span>
          ) : (
            <span className="text-xs font-bold text-gray-600">NONE</span>
          )}
        </div>
      </div>
    </div>
  );
}