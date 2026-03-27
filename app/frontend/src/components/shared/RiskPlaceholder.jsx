/**
 * RiskPlaceholder — shown in the main content area for the Risk Manager view.
 * Phase 6 will replace this with the real risk visualization.
 */
import { ShieldAlert, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { useRiskStore } from '../../stores/useRiskStore.js';
import { useOpsStore } from '../../stores/useOpsStore.js';

export default function RiskPlaceholder() {
  const { sessionPnl, winRate, totalTrades, currentStreak, maxDrawdown } = useRiskStore();
  const { balance, accountType } = useOpsStore();

  const pnlPositive = sessionPnl > 0;
  const pnlNegative = sessionPnl < 0;

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 p-8">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 rounded-2xl bg-amber-400/10 border border-amber-400/20 flex items-center justify-center mx-auto mb-4">
          <ShieldAlert size={28} className="text-amber-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2">
          Risk Manager
        </h2>
        <p className="text-xs text-slate-400 dark:text-slate-500 mb-6">
          Phase 6 — Full risk visualization coming next.
        </p>
      </div>

      {/* Session summary cards */}
      <div className="grid grid-cols-2 gap-3 w-full max-w-sm">
        {balance > 0 && (
          <SummaryCard
            label="Balance"
            value={`$${balance.toFixed(2)}`}
            sub={accountType ? `${accountType} account` : undefined}
            valueClass="text-slate-800 dark:text-slate-100"
          />
        )}

        <SummaryCard
          label="Session P&L"
          value={`${pnlPositive ? '+' : ''}$${sessionPnl.toFixed(2)}`}
          icon={pnlPositive ? TrendingUp : pnlNegative ? TrendingDown : Minus}
          valueClass={pnlPositive ? 'text-emerald-500' : pnlNegative ? 'text-red-500' : 'text-slate-500'}
        />

        <SummaryCard
          label="Win Rate"
          value={totalTrades > 0 ? `${winRate.toFixed(1)}%` : '—'}
          sub={totalTrades > 0 ? `${totalTrades} trades` : 'No trades yet'}
          valueClass={winRate >= 50 ? 'text-emerald-500' : totalTrades > 0 ? 'text-red-500' : 'text-slate-500'}
        />

        <SummaryCard
          label="Streak"
          value={currentStreak !== 0 ? `${currentStreak > 0 ? '+' : ''}${currentStreak}` : '—'}
          sub={currentStreak > 0 ? 'Win streak' : currentStreak < 0 ? 'Loss streak' : 'No streak'}
          valueClass={currentStreak > 0 ? 'text-emerald-500' : currentStreak < 0 ? 'text-red-500' : 'text-slate-500'}
        />

        <SummaryCard
          label="Max Drawdown"
          value={maxDrawdown > 0 ? `-$${maxDrawdown.toFixed(2)}` : '—'}
          valueClass={maxDrawdown > 0 ? 'text-red-500' : 'text-slate-500'}
        />
      </div>

      {totalTrades === 0 && (
        <p className="text-xs text-slate-400 text-center">
          No trades recorded this session.
        </p>
      )}
    </div>
  );
}

function SummaryCard({ label, value, sub, icon: Icon, valueClass = 'text-slate-800 dark:text-slate-100' }) {
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-3">
      <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-base font-bold flex items-center gap-1 ${valueClass}`}>
        {Icon && <Icon size={14} />}
        {value}
      </p>
      {sub && <p className="text-[10px] text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}
