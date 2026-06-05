import { useEffect, useMemo } from 'react';
import { Layers3, Target, Trophy, Zap, Wallet, BarChart3, CircleDollarSign, PlayCircle } from 'lucide-react';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { useRiskStore } from '../../stores/useRiskStore.js';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { resolveTradeStake, useTradingStore } from '../../stores/useTradingStore.js';
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
  const balance = useOpsStore((s) => s.balance);
  const accountType = useOpsStore((s) => s.accountType);
  const sessionStatus = useOpsStore((s) => s.sessionStatus);
  const initialBalance = useSettingsStore((s) => s.initialBalance);
  const payoutPercentage = useSettingsStore((s) => s.payoutPercentage);
  const riskPercentPerTrade = useSettingsStore((s) => s.riskPercentPerTrade);
  const drawdownPercent = useSettingsStore((s) => s.drawdownPercent);
  const riskRewardRatio = useSettingsStore((s) => s.riskRewardRatio);
  const useFixedAmount = useSettingsStore((s) => s.useFixedAmount);
  const fixedRiskAmount = useSettingsStore((s) => s.fixedRiskAmount);
  const selectedAsset = useAssetStore((s) => s.selectedAsset);
  const amount = useTradingStore((s) => s.amount);
  const amountType = useTradingStore((s) => s.amountType);
  const duration = useTradingStore((s) => s.duration);
  const isExecuting = useTradingStore((s) => s.isExecuting);
  const executeTrade = useTradingStore((s) => s.executeTrade);
  const setDirection = useTradingStore((s) => s.setDirection);
  const startBalance = useRiskStore((s) => s.startBalance);
  const currentBalance = useRiskStore((s) => s.currentBalance);
  const sessionPnl = useRiskStore((s) => s.sessionPnl);
  const sessionWins = useRiskStore((s) => s.sessionWins);
  const sessionLosses = useRiskStore((s) => s.sessionLosses);
  const sessionVoids = useRiskStore((s) => s.sessionVoids);
  const resolvedTrades = useRiskStore((s) => s.resolvedTrades);
  const totalTrades = useRiskStore((s) => s.totalTrades);
  const currentStreak = useRiskStore((s) => s.currentStreak);
  const maxDrawdown = useRiskStore((s) => s.maxDrawdown);
  const peakBalance = useRiskStore((s) => s.peakBalance);
  const winRate = useRiskStore((s) => s.winRate);
  const tradeRuns = useRiskStore((s) => s.tradeRuns);
  const currentTradeRun = useRiskStore((s) => s.currentTradeRun);
  const recordingMode = useRiskStore((s) => s.recordingMode);
  const syncStartBalance = useRiskStore((s) => s.syncStartBalance);
  const setRecordingMode = useRiskStore((s) => s.setRecordingMode);
  const recordTradeResult = useRiskStore((s) => s.recordTradeResult);
  const startNewTradeRun = useRiskStore((s) => s.startNewTradeRun);
  const overrideTradeResult = useRiskStore((s) => s.overrideTradeResult);
  const resetSession = useRiskStore((s) => s.resetSession);

  useEffect(() => {
    if (balance > 0 && startBalance === 0) {
      syncStartBalance(balance);
      return;
    }

    if (balance <= 0 && startBalance === 0 && initialBalance > 0) {
      syncStartBalance(initialBalance);
    }
  }, [balance, initialBalance, startBalance, syncStartBalance]);

  const metrics = useMemo(() => computeRiskMetrics({
    startBalance: startBalance || initialBalance,
    payoutPercentage,
    riskPercentPerTrade,
    drawdownPercent,
    riskRewardRatio,
    useFixedAmount,
    fixedRiskAmount,
    currentSessionPnl: sessionPnl,
  }), [
    startBalance,
    initialBalance,
    payoutPercentage,
    riskPercentPerTrade,
    drawdownPercent,
    riskRewardRatio,
    useFixedAmount,
    fixedRiskAmount,
    sessionPnl,
  ]);

  const tradeCountForRun = currentTradeRun?.trades?.length ?? 0;
  const canAddTrades = true;

  const resolvedStake = useMemo(() => {
    return resolveTradeStake({ amount, amountType, balance });
  }, [amount, amountType, balance]);

  const canExecuteTrade = sessionStatus === 'connected'
    && !isExecuting
    && Boolean(selectedAsset)
    && resolvedStake > 0
    && Number(duration) > 0;

  const handleExecute = (direction) => {
    if (!canExecuteTrade) return;
    setDirection(direction);
    void executeTrade('pocket_option', selectedAsset);
  };

  const handleAddTrade = (outcome) => {
    const riskAmount = useFixedAmount
      ? fixedRiskAmount
      : metrics.riskPerTrade;

    const pnl = outcome === 'win'
      ? riskAmount * (payoutPercentage / 100)
      : outcome === 'loss'
        ? -riskAmount
        : 0;

    recordTradeResult({
      outcome,
      pnl,
      stake: riskAmount,
      payoutPercentage,
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
          <ActionStatCard 
            label="To Target" 
            value={`$${Math.max(0, metrics.takeProfitTarget - currentBalance).toFixed(2)}`} 
            sub={`Target $${metrics.takeProfitTarget.toFixed(2)}`} 
            icon={Target} 
            tone="emerald" 
            actionLabel="CALL"
            disabled={!canExecuteTrade}
            onAction={() => handleExecute('call')}
          />
          <ActionStatCard 
            label="To Limit" 
            value={`$${Math.max(0, currentBalance - metrics.maxDrawdownLimit).toFixed(2)}`} 
            sub={`Limit $${metrics.maxDrawdownLimit.toFixed(2)}`} 
            icon={Layers3} 
            tone="rose"
            actionLabel="PUT"
            disabled={!canExecuteTrade}
            onAction={() => handleExecute('put')}
          />
          <StatCard label="Min Win Rate" value={`${metrics.minimumWinRate.toFixed(1)}%`} sub={`Risk/trade $${metrics.riskPerTrade.toFixed(2)}`} icon={Trophy} tone="amber" />
        </section>

        <section className="grid gap-4">
          <div className="flex flex-col gap-4">
            <SessionControls
              recordingMode={recordingMode}
              onModeChange={setRecordingMode}
              onAddTrade={handleAddTrade}
              onNewRun={startNewTradeRun}
              onSync={() => syncStartBalance(balance > 0 ? balance : initialBalance)}
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

function ActionStatCard({ label, value, sub, icon: Icon, tone = 'neutral', actionLabel, onAction, disabled = false }) {
  const toneClasses = {
    neutral: 'border-white/5 bg-[#10151a] text-[#e3e6e7] hover:bg-white/5',
    emerald: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-400 hover:bg-emerald-400/20 hover:border-emerald-400/40',
    amber: 'border-[#f5df19]/20 bg-[#f5df19]/10 text-[#f5df19] hover:bg-[#f5df19]/20',
    rose: 'border-red-400/20 bg-red-400/10 text-red-400 hover:bg-red-400/20 hover:border-red-400/40',
  };

  return (
    <button disabled={disabled} onClick={onAction} className={`flex text-left flex-col justify-center rounded-2xl border p-4 shadow-[0_8px_24px_rgba(0,0,0,0.18)] transition-colors duration-200 cursor-pointer disabled:cursor-not-allowed disabled:opacity-45 ${toneClasses[tone]}`}>
      <div className="flex items-start justify-between gap-3 w-full">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.26em] text-gray-500">{label}</p>
          <div className="flex items-center gap-2 mt-1">
            <p className="text-xl font-black tracking-tight text-[#e3e6e7]">{value}</p>
            {actionLabel && (
              <span className={`text-[11px] px-1.5 py-0.5 rounded-md font-black tracking-widest ${
                tone === 'emerald' ? 'bg-emerald-400/20 text-emerald-400' : 'bg-red-400/20 text-red-400'
              }`}>
                {actionLabel}
              </span>
            )}
          </div>
          {sub && <p className="mt-1 text-[11px] font-medium text-gray-500">{sub}</p>}
        </div>
        {Icon && (
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#0b0f13] text-[#f5df19] shadow-sm">
            <Icon size={16} />
          </div>
        )}
      </div>
    </button>
  );
}