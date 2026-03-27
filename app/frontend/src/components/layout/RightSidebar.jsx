/**
 * RightSidebar — collapsible info/risk panel.
 * Shows session risk summary when expanded.
 */
import { ChevronLeft, ChevronRight, TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';
import { useState } from 'react';
import { useRiskStore } from '../../stores/useRiskStore.js';
import { useOpsStore } from '../../stores/useOpsStore.js';

export default function RightSidebar() {
  const [open, setOpen] = useState(true);
  const { sessionPnl, winRate, totalTrades, currentStreak, maxDrawdown } = useRiskStore();
  const { balance, accountType } = useOpsStore();

  const pnlPositive = sessionPnl > 0;
  const pnlNegative = sessionPnl < 0;

  return (
    <aside className={`
      flex flex-col shrink-0
      border-l border-slate-200 dark:border-slate-700
      bg-white dark:bg-slate-900
      transition-all duration-200
      ${open ? 'w-52' : 'w-12'}
    `}>
      {/* Toggle button */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-center h-10 w-full border-b border-slate-200 dark:border-slate-700 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors shrink-0"
        title={open ? 'Collapse panel' : 'Expand panel'}
      >
        {open ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      {open && (
        <div className="flex flex-col gap-3 p-3 overflow-y-auto">
          {/* Header */}
          <div className="flex items-center gap-1.5">
            <Activity size={12} className="text-slate-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Session Risk</span>
          </div>

          {/* Balance */}
          {balance > 0 && (
            <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-2.5">
              <p className="text-[10px] text-slate-400 mb-0.5">Balance</p>
              <p className="text-sm font-bold text-slate-800 dark:text-slate-100">
                ${balance.toFixed(2)}
              </p>
              {accountType && (
                <p className="text-[10px] text-slate-400 capitalize">{accountType} account</p>
              )}
            </div>
          )}

          {/* Session P&L */}
          <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-2.5">
            <p className="text-[10px] text-slate-400 mb-0.5">Session P&L</p>
            <p className={`text-sm font-bold flex items-center gap-1 ${
              pnlPositive ? 'text-emerald-500' : pnlNegative ? 'text-red-500' : 'text-slate-500'
            }`}>
              {pnlPositive ? <TrendingUp size={13} /> : pnlNegative ? <TrendingDown size={13} /> : <Minus size={13} />}
              {pnlPositive ? '+' : ''}{sessionPnl.toFixed(2)}
            </p>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-2">
            <StatCard label="Win Rate" value={totalTrades > 0 ? `${winRate.toFixed(0)}%` : '—'} />
            <StatCard label="Trades" value={totalTrades > 0 ? totalTrades : '—'} />
            <StatCard
              label="Streak"
              value={currentStreak !== 0 ? `${currentStreak > 0 ? '+' : ''}${currentStreak}` : '—'}
              valueClass={currentStreak > 0 ? 'text-emerald-500' : currentStreak < 0 ? 'text-red-500' : 'text-slate-500'}
            />
            <StatCard
              label="Max DD"
              value={maxDrawdown > 0 ? `-$${maxDrawdown.toFixed(2)}` : '—'}
              valueClass={maxDrawdown > 0 ? 'text-red-500' : 'text-slate-500'}
            />
          </div>

          {totalTrades === 0 && (
            <p className="text-[10px] text-slate-400 text-center py-2">
              No trades this session
            </p>
          )}
        </div>
      )}
    </aside>
  );
}

function StatCard({ label, value, valueClass = 'text-slate-800 dark:text-slate-100' }) {
  return (
    <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-2">
      <p className="text-[9px] text-slate-400 mb-0.5 uppercase tracking-wide">{label}</p>
      <p className={`text-xs font-bold ${valueClass}`}>{value}</p>
    </div>
  );
}
