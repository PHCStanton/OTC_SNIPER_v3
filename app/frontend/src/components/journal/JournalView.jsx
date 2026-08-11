import React, { useState, useEffect } from 'react';
import { 
  BookOpen, 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  Target, 
  BarChart2, 
  Download,
  Filter,
  Layers,
  Database,
  RefreshCw,
  Sparkles
} from 'lucide-react';
import { useRiskStore } from '../../stores/useRiskStore.js';
import DateRangePicker from './DateRangePicker.jsx';

import StatCard from './StatCard.jsx';
import OTEOEfficiency from './OTEOEfficiency.jsx';
import StreakAnalytics from './StreakAnalytics.jsx';
import TradeHistoryTable from './TradeHistoryTable.jsx';
import EquityCurve from './EquityCurve.jsx';

import LiquidityVolatilityGauges from './LiquidityVolatilityGauges.jsx';
import AssetManipulationStats from './AssetManipulationStats.jsx';
import FavouredRegimesCard from './FavouredRegimesCard.jsx';
import AdaptiveExpiriesCard from './AdaptiveExpiriesCard.jsx';
import AISessionBriefingCard from './AISessionBriefingCard.jsx';
import KnowledgeBaseStagingModal from './KnowledgeBaseStagingModal.jsx';

export default function JournalView() {
  const ghostTrades = useRiskStore((s) => s.ghostTrades);
  const ghostWins = useRiskStore((s) => s.ghostWins);
  const ghostLosses = useRiskStore((s) => s.ghostLosses);
  const ghostPnl = useRiskStore((s) => s.ghostPnl);
  const ghostWinRate = useRiskStore((s) => s.ghostWinRate);
  const autoGhostMetrics = useRiskStore((s) => s.autoGhostMetrics);

  const [selectedSessionId, setSelectedSessionId] = useState('ALL');
  const [sessionList, setSessionList] = useState([]);
  const [journalStats, setJournalStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [isStagingModalOpen, setIsStagingModalOpen] = useState(false);
  const [dateFrom, setDateFrom] = useState(null);
  const [dateTo, setDateTo] = useState(null);

  // Fetch available sessions
  const loadSessions = async () => {
    try {
      const res = await fetch('/api/analysis/sessions');
      if (!res.ok) return;
      const data = await res.json();
      const ghost = data.ghost_sessions || [];
      setSessionList(ghost);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  };

  // Fetch quantitative journal stats for the chosen session / date range
  const fetchJournalStats = async (sessionId, from, to) => {
    setStatsLoading(true);
    try {
      let url = `/api/analysis/journal-stats?kind=ghost`;
      // Date range takes precedence over session ID
      if (from || to) {
        if (from) url += `&date_from=${from}`;
        if (to)   url += `&date_to=${to}`;
      } else if (sessionId && sessionId !== 'ALL') {
        url += `&session_id=${sessionId}`;
      }
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setJournalStats(data);
    } catch (err) {
      console.error('Failed to fetch journal stats:', err);
    } finally {
      setStatsLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
    fetchJournalStats(selectedSessionId, dateFrom, dateTo);
  }, [selectedSessionId, dateFrom, dateTo]);

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

  // Metrics to display (dynamic from stats if loaded, or store fallback)
  const displayPnl = journalStats ? journalStats.total_profit : ghostPnl;
  const displayWins = journalStats ? journalStats.wins : ghostWins;
  const displayLosses = journalStats ? journalStats.losses : ghostLosses;
  const displayWinRate = journalStats ? journalStats.win_rate : ghostWinRate;

  return (
    <div className="flex flex-col flex-1 h-full bg-[#0c0f0f] overflow-hidden">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between px-6 py-3.5 border-b border-white/5 bg-[#171a22] gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/20">
            <BookOpen size={20} />
          </div>
          <div>
            <h1 className="text-md font-black uppercase tracking-wider text-white">Trading Journal</h1>
            <p className="text-[10px] font-black uppercase tracking-widest text-[#ffb800]">
              Quantitative Microstructure Analytics & Knowledge Staging
            </p>
          </div>
        </div>

        {/* Controls Bar */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Calendar Date Range Picker */}
          <DateRangePicker
            dateFrom={dateFrom}
            dateTo={dateTo}
            onChange={({ from, to }) => {
              setDateFrom(from);
              setDateTo(to);
              // When a date range is active, reset session selector to ALL
              if (from || to) setSelectedSessionId('ALL');
            }}
          />

          {/* Session Selector — secondary filter (only meaningful when no date range active) */}
          {!dateFrom && !dateTo && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#21242c] border border-white/5 text-xs">
              <Layers size={13} className="text-gray-400" />
              <select
                value={selectedSessionId}
                onChange={(e) => setSelectedSessionId(e.target.value)}
                className="bg-transparent text-white font-mono text-[11px] outline-none cursor-pointer"
              >
                <option value="ALL" className="bg-[#21242c] text-amber-400">
                  ⭐ Multi-Session Aggregate (All Data)
                </option>
                {sessionList.map((s) => (
                  <option key={s.session_id} value={s.session_id} className="bg-[#21242c] text-gray-200">
                    {s.session_id} ({s.total_trades} trades, {s.win_rate.toFixed(0)}% WR)
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={() => fetchJournalStats(selectedSessionId, dateFrom, dateTo)}
            className="p-2 rounded-lg bg-[#25282f] border border-white/5 text-gray-400 hover:text-white hover:bg-[#2d3139] transition-all"
            title="Refresh Analytics"
          >
            <RefreshCw size={13} className={statsLoading ? 'animate-spin' : ''} />
          </button>

          {/* Staging & Review Modal Trigger */}
          <button
            onClick={() => setIsStagingModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-amber-500/20 to-emerald-500/20 border border-amber-500/30 text-[10px] font-black uppercase tracking-wider text-amber-300 hover:text-white hover:border-amber-400 transition-all shadow-md shadow-amber-500/10"
          >
            <Database size={13} />
            <span>KB Staging & Review</span>
          </button>
        </div>
      </div>

      {/* Main Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
        
        {/* Core Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            label="Net Profit" 
            value={`$${displayPnl.toFixed(2)}`} 
            subValue={`${displayWins}W / ${displayLosses}L`}
            icon={<BarChart2 size={18} />}
            trend={displayPnl >= 0 ? 'up' : 'down'}
          />
          <StatCard 
            label="Win Rate" 
            value={`${displayWinRate.toFixed(1)}%`} 
            subValue={selectedSessionId === 'ALL' ? `All Sessions (${journalStats?.sessions_count || 0})` : 'Selected Session'}
            icon={<Target size={18} />}
            color={displayWinRate >= 50 ? 'text-emerald-400' : 'text-rose-400'}
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

        {/* AI Session Briefing & Advisory Card */}
        <AISessionBriefingCard
          stats={journalStats}
          sessionId={selectedSessionId}
          kind="ghost"
          onOpenStagingModal={() => setIsStagingModalOpen(true)}
        />

        {/* Liquidity & Volatility Microstructure Gauges */}
        <LiquidityVolatilityGauges stats={journalStats} />

        {/* Asset Manipulation Leaderboard & Favoured Regimes Ranking */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <AssetManipulationStats stats={journalStats} />
          <FavouredRegimesCard stats={journalStats} />
        </div>

        {/* Adaptive Expiries & Classic Journal Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <AdaptiveExpiriesCard stats={journalStats} />
          <OTEOEfficiency ghostTrades={ghostTrades} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <StreakAnalytics autoGhostMetrics={autoGhostMetrics} />
          <EquityCurve ghostTrades={ghostTrades} />
        </div>

        {/* Recent Trades Table */}
        <TradeHistoryTable ghostTrades={ghostTrades} />
      </div>

      {/* Knowledge Base Staging & Review Modal */}
      <KnowledgeBaseStagingModal
        isOpen={isStagingModalOpen}
        onClose={() => setIsStagingModalOpen(false)}
      />
    </div>
  );
}