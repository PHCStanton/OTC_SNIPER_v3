import React from 'react';
import { 
  BookOpen, 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  Target, 
  BarChart2, 
  Download,
  Filter
} from 'lucide-react';
import { useRiskStore } from '../../stores/useRiskStore.js';

import StatCard from './StatCard.jsx';
import OTEOEfficiency from './OTEOEfficiency.jsx';
import StreakAnalytics from './StreakAnalytics.jsx';
import TradeHistoryTable from './TradeHistoryTable.jsx';
import EquityCurve from './EquityCurve.jsx';

export default function JournalView() {
  const ghostTrades = useRiskStore((s) => s.ghostTrades);
  const ghostWins = useRiskStore((s) => s.ghostWins);
  const ghostLosses = useRiskStore((s) => s.ghostLosses);
  const ghostPnl = useRiskStore((s) => s.ghostPnl);
  const ghostWinRate = useRiskStore((s) => s.ghostWinRate);
  const autoGhostMetrics = useRiskStore((s) => s.autoGhostMetrics);

  // Use real backend autoGhostMetrics for streaks and recovery time
  const currentStreakCount = autoGhostMetrics?.auto_ghost_current_streak_count || 0;
  const currentStreakType = autoGhostMetrics?.auto_ghost_current_streak_type || null;
  const currentStreakLabel = currentStreakType 
    ? `${currentStreakCount} ${currentStreakType.toUpperCase()}` 
    : 'NONE';

  const isWinningStreak = currentStreakType === 'win';
  
  const avgRecoveryTime = autoGhostMetrics?.auto_ghost_avg_recovery_time_mins 
    ? `${autoGhostMetrics.auto_ghost_avg_recovery_time_mins}m` 
    : '--';

  return (
    <div className="flex flex-col flex-1 h-full bg-[#0c0f0f] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-[#1a1c22]">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/20">
            <BookOpen size={20} />
          </div>
          <div>
            <h1 className="text-md font-black uppercase tracking-wider text-white">Trading Journal</h1>
            <p className="text-[10px] font-black uppercase tracking-widest text-[#ffb800]">Ghost Session Analysis</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#25282f] border border-white/5 text-[10px] font-black uppercase tracking-widest text-gray-400 hover:bg-[#2d3139] hover:text-white transition-all">
            <Filter size={12} />
            Filter
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#ffb800]/10 border border-[#ffb800]/25 text-[10px] font-black uppercase tracking-widest text-[#ffb800] hover:bg-[#ffb800]/20 transition-all">
            <Download size={12} />
            Export Report
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
        
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            label="Net Profit" 
            value={`$${ghostPnl.toFixed(2)}`} 
            subValue={`${ghostWins}W / ${ghostLosses}L`}
            icon={<BarChart2 size={18} />}
            trend={ghostPnl >= 0 ? 'up' : 'down'}
          />
          <StatCard 
            label="Win Rate" 
            value={`${ghostWinRate.toFixed(1)}%`} 
            subValue="Ghost Trades"
            icon={<Target size={18} />}
            color={ghostWinRate >= 50 ? 'text-emerald-400' : 'text-rose-400'}
          />
          <StatCard 
            label="Current Streak" 
            value={currentStreakLabel} 
            subValue={isWinningStreak ? 'Winning' : currentStreakType === 'loss' ? 'Losing' : 'Neutral'}
            icon={isWinningStreak ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
            color={isWinningStreak ? 'text-emerald-400' : currentStreakType === 'loss' ? 'text-rose-400' : 'text-gray-400'}
          />
          <StatCard 
            label="Avg Recovery" 
            value={avgRecoveryTime} 
            subValue="Between Loss Streaks"
            icon={<Clock size={18} />}
          />
        </div>

        {/* Streak Analysis, OTEO Efficiency, and Equity Curve */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <StreakAnalytics autoGhostMetrics={autoGhostMetrics} />
          <OTEOEfficiency ghostTrades={ghostTrades} />
          <EquityCurve ghostTrades={ghostTrades} />
        </div>

        {/* Recent Trades Table */}
        <TradeHistoryTable ghostTrades={ghostTrades} />
      </div>
    </div>
  );
}