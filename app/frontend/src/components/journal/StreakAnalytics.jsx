import React from 'react';
import { TrendingUp } from 'lucide-react';

export default function StreakAnalytics({ autoGhostMetrics }) {
  // Use real backend data if available, fallback to empty stats
  const maxWinStreak = autoGhostMetrics?.auto_ghost_max_win_streak || 0;
  const maxLossStreak = autoGhostMetrics?.auto_ghost_max_loss_streak || 0;
  const currentStreak = autoGhostMetrics?.auto_ghost_current_streak_count || 0;
  const currentType = autoGhostMetrics?.auto_ghost_current_streak_type || null;

  return (
    <div className="bg-[#1a1c22] border border-white/5 rounded-xl p-5 transition hover:border-white/10">
      <h3 className="text-[10px] font-black text-gray-500 mb-4 flex items-center gap-2 uppercase tracking-widest">
        <TrendingUp size={16} className="text-[#ffb800]" />
        Streak Distribution
      </h3>
      <div className="flex flex-col gap-5">
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-emerald-500/10 border border-emerald-500/25 rounded-lg p-4 text-center">
            <p className="text-[9px] text-emerald-500 font-black uppercase tracking-widest">Max Win Streak</p>
            <p className="text-2xl font-black text-emerald-400 mt-2">{maxWinStreak}</p>
          </div>
          <div className="bg-rose-500/10 border border-rose-500/25 rounded-lg p-4 text-center">
            <p className="text-[9px] text-rose-500 font-black uppercase tracking-widest">Max Loss Streak</p>
            <p className="text-2xl font-black text-rose-400 mt-2">{maxLossStreak}</p>
          </div>
        </div>
        
        <div className="flex items-center justify-between p-4 bg-[#25282f]/30 rounded-lg border border-white/5">
          <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Current Active Streak</span>
          {currentType ? (
            <span className={`text-[9px] font-black px-2.5 py-1 rounded border ${
              currentType === 'win' 
                ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400' 
                : 'border-rose-500/20 bg-rose-500/10 text-rose-400'
            }`}>
              {currentStreak} {currentType.toUpperCase()}
            </span>
          ) : (
            <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">NONE</span>
          )}
        </div>
      </div>
    </div>
  );
}