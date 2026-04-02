/**
 * RightSidebar — collapsible info/risk panel.
 * Shows session risk summary and AI assistant tabs when expanded.
 */
import { ChevronLeft, ChevronRight, TrendingUp, TrendingDown, Minus, Activity, Target } from 'lucide-react';
import { useMemo } from 'react';
import { useRiskStore } from '../../stores/useRiskStore.js';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useLayoutStore } from '../../stores/useLayoutStore.js';
import { computeRiskMetrics } from '../../utils/riskMath.js';
import VerticalRiskChart from '../risk/VerticalRiskChart.jsx';

export default function RightSidebar() {
  const { rightSidebarOpen, toggleRightSidebar } = useLayoutStore();
  const { sessionPnl, winRate, totalTrades, startBalance, currentBalance } = useRiskStore();
  const settings = useSettingsStore();

  const pnlPositive = sessionPnl > 0;
  const pnlNegative = sessionPnl < 0;

  const metrics = useMemo(() => computeRiskMetrics({
    startBalance: startBalance || settings.initialBalance,
    payoutPercentage: settings.payoutPercentage,
    riskPercentPerTrade: settings.riskPercentPerTrade,
    drawdownPercent: settings.drawdownPercent,
    riskRewardRatio: settings.riskRewardRatio,
    useFixedAmount: settings.useFixedAmount,
    fixedRiskAmount: settings.fixedRiskAmount,
    currentSessionPnl: sessionPnl,
  }), [
    startBalance,
    settings.initialBalance,
    settings.payoutPercentage,
    settings.riskPercentPerTrade,
    settings.drawdownPercent,
    settings.riskRewardRatio,
    settings.useFixedAmount,
    settings.fixedRiskAmount,
    sessionPnl,
  ]);

  return (
    <aside className={`
      flex flex-col shrink-0
      border-l border-white/5
      bg-[#0f1419]
      transition-all duration-200
      ${rightSidebarOpen ? 'w-[280px]' : 'w-12'}
    `}>
      {/* Toggle button */}
      <button
        onClick={toggleRightSidebar}
        className="flex items-center justify-center h-10 w-full border-b border-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-colors shrink-0"
        title={rightSidebarOpen ? 'Collapse panel' : 'Expand panel'}
      >
        {rightSidebarOpen ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
      </button>

      {rightSidebarOpen && (
        <div className="flex flex-col gap-3 p-3 overflow-y-auto custom-scrollbar flex-1">
          <div className="flex items-center gap-1.5 px-1 py-1">
            <Activity size={14} className="text-[#f5df19]" />
            <span className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#f5df19]">Session Risk</span>
          </div>

          <div className="bg-[#151a22] border border-white/5 shadow-md rounded-xl p-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-gray-500 mb-1">Session P&L</p>
            <p className={`text-xl font-black flex items-center gap-1.5 ${
              pnlPositive ? 'text-emerald-500' : pnlNegative ? 'text-red-500' : 'text-[#e3e6e7]'
            }`}>
              {pnlPositive ? <TrendingUp size={18} /> : pnlNegative ? <TrendingDown size={18} /> : <Minus size={18} />}
              {pnlPositive ? '+' : ''}{sessionPnl.toFixed(2)}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <MetricCard label="To Target" value={`$${Math.max(0, metrics.takeProfitTarget - currentBalance).toFixed(2)}`} tone="emerald" icon={Target} />
            <MetricCard label="To Limit" value={`$${Math.max(0, currentBalance - metrics.maxDrawdownLimit).toFixed(2)}`} tone="rose" icon={Target} />
          </div>

          <div className="mt-2 mb-2 flex-1 min-h-[300px] flex flex-col">
            <VerticalRiskChart
              startBalance={metrics.startBalance}
              currentBalance={currentBalance}
              takeProfitTarget={metrics.takeProfitTarget}
              maxDrawdownLimit={metrics.maxDrawdownLimit}
              height={380}
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <StatCard label="Win Rate" value={totalTrades > 0 ? `${winRate.toFixed(0)}%` : '—'} />
            <StatCard label="Trades" value={totalTrades > 0 ? totalTrades : '—'} />
          </div>

          {totalTrades === 0 && (
            <p className="text-[10px] text-gray-500 text-center py-4 font-medium uppercase tracking-wider">
              No trades this session
            </p>
          )}
        </div>
      )}
    </aside>
  );
}

function StatCard({ label, value, valueClass = 'text-[#e3e6e7]' }) {
  return (
    <div className="bg-[#151a22] border border-white/5 shadow-sm rounded-xl p-2.5">
      <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-gray-500 mb-1">{label}</p>
      <p className={`text-sm font-bold ${valueClass}`}>{value}</p>
    </div>
  );
}

function MetricCard({ label, value, tone = 'slate', icon: Icon }) {
  const toneClasses = {
    emerald: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-400',
    rose: 'border-red-400/20 bg-red-400/10 text-red-400',
    slate: 'border-white/5 bg-white/5 text-[#e3e6e7]',
  };

  return (
    <div className={`rounded-xl border px-3 py-2 ${toneClasses[tone]}`}>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.18em] opacity-70">
        {Icon && <Icon size={10} />}
        {label}
      </div>
      <div className="mt-1 text-sm font-bold tracking-tight">{value}</div>
    </div>
  );
}
