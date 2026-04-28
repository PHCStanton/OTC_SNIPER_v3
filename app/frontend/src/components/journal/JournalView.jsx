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
  const { 
    ghostTrades, 
    ghostWins, 
    ghostLosses, 
    ghostPnl,
    ghostWinRate,
    autoGhostMetrics
  } = useRiskStore();

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
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-[#141818]/50">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#f5df19]/10 text-[#f5df19]">
            <BookOpen size={20} />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-gray-100">Trading Journal</h1>
            <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold">Ghost Session Analysis</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-white/5 border border-white/10 text-xs font-medium text-gray-400 hover:bg-white/10 hover:text-white transition-all">
            <Filter size={14} />
            Filter
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[#f5df19]/10 border border-[#f5df19]/20 text-xs font-medium text-[#f5df19] hover:bg-[#f5df19]/20 transition-all">
            <Download size={14} />
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