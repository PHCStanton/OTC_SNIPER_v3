import { useEffect, useMemo } from 'react';
import { Layers3, Target, Trophy, Zap, Wallet, BarChart3, CircleDollarSign, PlayCircle } from 'lucide-react';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { useRiskStore } from '../../stores/useRiskStore.js';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { computeRiskMetrics } from '../../utils/riskMath.js';
import SessionControls from './SessionControls.jsx';
import TradeRunHistory from './TradeRunHistory.jsx';

function StatCard({ label, value, sub, icon: Icon, tone = 'neutral' }) {
  const toneClasses = {
    neutral: 'border-white/5 bg-[#10151a] text-[#e3e6e7]',
    emerald: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-400',
    amber: 'border-[#f5df19]/20 bg-[#f5df19]/10 text-[#f5df19]',
    rose: 'border-red-400/20 bg-red-400/10 text-red-400',
  };

  return (
    <div className={`rounded-2xl border p-4 shadow-[0_8px_24px_rgba(0,0,0,0.18)] ${toneClasses[tone]}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.26em] text-gray-500">{label}</p>
          <p className="mt-1 text-xl font-black tracking-tight text-[#e3e6e7]">{value}</p>
          {sub && <p className="mt-1 text-[11px] font-medium text-gray-500">{sub}</p>}
        </div>
        {Icon && (
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#0b0f13] text-[#f5df19] shadow-sm">
            <Icon size={16} />
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryChip({ label, value }) {
  return (
    <div className="rounded-xl border border-white/5 bg-white/5 px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">{label}</p>
      <p className="mt-1 text-sm font-bold text-[#e3e6e7]">{value}</p>
    </div>
  );
}

export default function SessionRiskPanel() {
  const { balance, accountType } = useOpsStore();
  const settings = useSettingsStore();
  const {
    startBalance,
    currentBalance,
    sessionPnl,
    sessionWins,
    sessionLosses,
    sessionVoids,
    resolvedTrades,
    totalTrades,
    currentStreak,
    maxDrawdown,
    peakBalance,
    winRate,
    tradeRuns,
    currentTradeRun,
    recordingMode,
    syncStartBalance,
    setRecordingMode,
    recordTradeResult,
    startNewTradeRun,
    overrideTradeResult,
    resetSession,
  } = useRiskStore();

  useEffect(() => {
    if (balance > 0 && startBalance === 0) {
      syncStartBalance(balance);
      return;
    }

    if (balance <= 0 && startBalance === 0 && settings.initialBalance > 0) {
      syncStartBalance(settings.initialBalance);
    }
  }, [balance, settings.initialBalance, startBalance, syncStartBalance]);

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

  const tradeCountForRun = currentTradeRun?.trades?.length ?? 0;
  const canAddTrades = true;

  const handleAddTrade = (outcome) => {
    const riskAmount = settings.useFixedAmount
      ? settings.fixedRiskAmount
      : metrics.riskPerTrade;

    const pnl = outcome === 'win'
      ? riskAmount * (settings.payoutPercentage / 100)
      : outcome === 'loss'
        ? -riskAmount
        : 0;

    recordTradeResult({
      outcome,
      pnl,
      stake: riskAmount,
      payoutPercentage: settings.payoutPercentage,
      source: 'manual',
    });
  };

  const handleCycleTradeResult = (runId, tradeId, currentOutcome) => {
    const cycleOrder = ['win', 'loss', 'void'];
    const currentIndex = cycleOrder.indexOf(currentOutcome);
    const nextOutcome = cycleOrder[(currentIndex + 1) % cycleOrder.length];
    overrideTradeResult(runId, tradeId, nextOutcome);
  };

  const handleExport = () => {
    const rows = [
      ['run_id', 'trade_id', 'outcome', 'stake', 'payout_percentage', 'pnl', 'edited', 'source', 'created_at'],
    ];

    [...tradeRuns, currentTradeRun].forEach((run) => {
      run.trades.forEach((trade) => {
        rows.push([
          run.id,
          trade.id,
          trade.outcome,
          trade.stake,
          trade.payoutPercentage,
          trade.pnl,
          trade.edited ? 'yes' : 'no',
          trade.source,
          trade.createdAt,
        ]);
      });
    });

    const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'session-risk-history.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const handleReset = () => {
    resetSession();
    if (balance > 0) {
      syncStartBalance(balance);
    }
  };

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top,_rgba(245,223,25,0.08),_transparent_32%),linear-gradient(180deg,#0c0f0f_0%,#10151a_46%,#131820_100%)] px-4 py-4 text-[#e3e6e7] lg:px-6 lg:py-6">
      <div className="mx-auto flex max-w-[1700px] flex-col gap-4">
        <div className="rounded-3xl border border-white/5 bg-[#151a22]/95 px-5 py-4 shadow-[0_15px_40px_rgba(0,0,0,0.28)]">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#f5df19] text-black shadow-lg shadow-[#f5df19]/20">
                  <BarChart3 size={20} />
                </div>
                <div>
                  <h2 className="text-lg font-bold tracking-tight text-[#e3e6e7]">Risk Manager</h2>
                  <p className="text-xs text-gray-500">Trade, Trade Run, and Session control surface</p>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <SummaryChip label="Mode" value={recordingMode.toUpperCase()} />
                <SummaryChip label="Account" value={accountType ? accountType.toUpperCase() : '—'} />
                <SummaryChip label="Starting Balance" value={`$${metrics.startBalance.toFixed(2)}`} />
                <SummaryChip label="Current Balance" value={`$${currentBalance.toFixed(2)}`} />
              </div>
            </div>

            <div className="grid min-w-[260px] gap-2 text-right sm:grid-cols-2 sm:text-left">
              <StatCard label="Session P/L" value={`${sessionPnl >= 0 ? '+' : ''}$${sessionPnl.toFixed(2)}`} sub={`${currentStreak > 0 ? `${currentStreak} win streak` : currentStreak < 0 ? `${Math.abs(currentStreak)} loss streak` : 'No active streak'}`} icon={sessionPnl >= 0 ? Zap : Wallet} tone={sessionPnl >= 0 ? 'emerald' : 'rose'} />
              <StatCard label="Win Rate" value={resolvedTrades > 0 ? `${winRate.toFixed(1)}%` : '—'} sub={`${sessionWins} wins · ${sessionLosses} losses · ${sessionVoids} voids`} icon={Trophy} tone={winRate >= 50 ? 'amber' : 'neutral'} />
            </div>
          </div>
        </div>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Balance" value={`$${currentBalance.toFixed(2)}`} sub={`Peak $${peakBalance.toFixed(2)}`} icon={CircleDollarSign} tone="neutral" />
          <StatCard label="To Target" value={`$${Math.max(0, metrics.takeProfitTarget - currentBalance).toFixed(2)}`} sub={`Target $${metrics.takeProfitTarget.toFixed(2)}`} icon={Target} tone="emerald" />
          <StatCard label="To Limit" value={`$${Math.max(0, currentBalance - metrics.maxDrawdownLimit).toFixed(2)}`} sub={`Limit $${metrics.maxDrawdownLimit.toFixed(2)}`} icon={Layers3} tone="rose" />
          <StatCard label="Min Win Rate" value={`${metrics.minimumWinRate.toFixed(1)}%`} sub={`Risk/trade $${metrics.riskPerTrade.toFixed(2)}`} icon={Trophy} tone="amber" />
        </section>

        <section className="grid gap-4">
          <div className="flex flex-col gap-4">
            <SessionControls
              recordingMode={recordingMode}
              onModeChange={setRecordingMode}
              onAddTrade={handleAddTrade}
              onNewRun={startNewTradeRun}
              onSync={() => syncStartBalance(balance > 0 ? balance : settings.initialBalance)}
              onExport={handleExport}
              onReset={handleReset}
              canAddTrades={canAddTrades}
            />

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <StatCard label="Total Trades" value={totalTrades} sub={`${tradeCountForRun} active in current run`} icon={BarChart3} tone="neutral" />
              <StatCard label="Resolved Trades" value={resolvedTrades} sub="Excludes VOID from win-rate math" icon={PlayCircle} tone="neutral" />
              <StatCard label="Current Streak" value={currentStreak === 0 ? '—' : `${currentStreak > 0 ? '+' : ''}${currentStreak}`} sub={currentStreak === 0 ? 'No streak' : currentStreak > 0 ? 'Win streak' : 'Loss streak'} icon={Zap} tone={currentStreak === 0 ? 'neutral' : currentStreak > 0 ? 'emerald' : 'rose'} />
              <StatCard label="Max Drawdown" value={`-$${maxDrawdown.toFixed(2)}`} sub={`Peak to trough drop`} icon={Wallet} tone={maxDrawdown > 0 ? 'rose' : 'neutral'} />
              <StatCard label="Void Trades" value={sessionVoids} sub="Break-even or corrected entries" icon={CircleDollarSign} tone="amber" />
            </div>

            <TradeRunHistory
              tradeRuns={tradeRuns}
              currentTradeRun={currentTradeRun}
              onCycleTradeResult={handleCycleTradeResult}
            />
          </div>
        </section>
      </div>
    </div>
  );
}