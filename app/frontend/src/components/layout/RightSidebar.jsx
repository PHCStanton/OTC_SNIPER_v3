/**
 * RightSidebar — collapsible info/risk panel.
 * Shows session risk summary and AI assistant tabs when expanded.
 */
import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, TrendingUp, TrendingDown, Minus, Activity, Target, ArrowUp, ArrowDown, RefreshCw } from 'lucide-react';
import { useRiskStore } from '../../stores/useRiskStore.js';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useLayoutStore } from '../../stores/useLayoutStore.js';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { resolveTradeStake, useTradingStore } from '../../stores/useTradingStore.js';
import { computeRiskMetrics } from '../../utils/riskMath.js';
import VerticalRiskChart from '../risk/VerticalRiskChart.jsx';
import MiniTradeRunHistory from '../risk/MiniTradeRunHistory.jsx';

export default function RightSidebar() {
  const [activeView, setActiveView] = useState('chart');
  const { rightSidebarOpen, toggleRightSidebar } = useLayoutStore();
  const sessionPnl = useRiskStore((s) => s.sessionPnl);
  const winRate = useRiskStore((s) => s.winRate);
  const totalTrades = useRiskStore((s) => s.totalTrades);
  const startBalance = useRiskStore((s) => s.startBalance);
  const currentBalance = useRiskStore((s) => s.currentBalance);
  const tradeRuns = useRiskStore((s) => s.tradeRuns);
  const currentTradeRun = useRiskStore((s) => s.currentTradeRun);
  const overrideTradeResult = useRiskStore((s) => s.overrideTradeResult);
  const resetSession = useRiskStore((s) => s.resetSession);
  const syncStartBalance = useRiskStore((s) => s.syncStartBalance);
  const initialBalance = useSettingsStore((s) => s.initialBalance);
  const payoutPercentage = useSettingsStore((s) => s.payoutPercentage);
  const riskPercentPerTrade = useSettingsStore((s) => s.riskPercentPerTrade);
  const drawdownPercent = useSettingsStore((s) => s.drawdownPercent);
  const riskRewardRatio = useSettingsStore((s) => s.riskRewardRatio);
  const useFixedAmount = useSettingsStore((s) => s.useFixedAmount);
  const fixedRiskAmount = useSettingsStore((s) => s.fixedRiskAmount);
  const sessionStatus = useOpsStore((s) => s.sessionStatus);
  const balance = useOpsStore((s) => s.balance);
  const selectedAsset = useAssetStore((s) => s.selectedAsset);
  const amount = useTradingStore((s) => s.amount);
  const amountType = useTradingStore((s) => s.amountType);
  const duration = useTradingStore((s) => s.duration);
  const isExecuting = useTradingStore((s) => s.isExecuting);
  const executeTrade = useTradingStore((s) => s.executeTrade);
  const setDirection = useTradingStore((s) => s.setDirection);

  const pnlPositive = sessionPnl > 0;
  const pnlNegative = sessionPnl < 0;

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

  const handleCycleTradeResult = (runId, tradeId, currentOutcome) => {
    const cycleOrder = ['win', 'loss', 'void'];
    const currentIndex = cycleOrder.indexOf(currentOutcome);
    const nextOutcome = cycleOrder[(currentIndex + 1) % cycleOrder.length];
    overrideTradeResult(runId, tradeId, nextOutcome);
  };

  const handleResetSession = () => {
    resetSession();
    if (balance > 0) {
      syncStartBalance(balance);
    } else if (initialBalance > 0) {
      syncStartBalance(initialBalance);
    }
  };

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
          <div className="flex items-center justify-between px-1 py-1">
            <div className="flex items-center gap-1.5">
              <Activity size={14} className="text-[#ffb800]" />
              <span className="text-[11px] font-black uppercase tracking-[0.2em] text-[#ffb800]">Session Risk</span>
            </div>

            <div className={`flex items-center gap-1 text-sm font-black tracking-tight ${
              pnlPositive ? 'text-emerald-500' : pnlNegative ? 'text-red-500' : 'text-slate-400'
            }`}>
              {pnlPositive ? <TrendingUp size={14} /> : pnlNegative ? <TrendingDown size={14} /> : <Minus size={14} />}
              <span className="font-mono">{pnlPositive ? '+' : ''}{sessionPnl.toFixed(2)}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <ActionMetricCard 
              label="To Target" 
              value={`$${Math.max(0, metrics.takeProfitTarget - currentBalance).toFixed(2)}`} 
              tone="emerald" 
              icon={Target}
              actionLabel="CALL"
              disabled={!canExecuteTrade}
              onAction={() => handleExecute('call')}
            />
            <ActionMetricCard 
              label="To Limit" 
              value={`$${Math.max(0, currentBalance - metrics.maxDrawdownLimit).toFixed(2)}`} 
              tone="rose" 
              icon={Target}
              actionLabel="PUT"
              disabled={!canExecuteTrade}
              onAction={() => handleExecute('put')}
            />
          </div>

          <div className="flex items-center gap-2 mt-1">
            <button
              onClick={handleResetSession}
              className="p-2 rounded-lg border border-white/5 bg-[#1e222b]/50 text-[#ffb800] hover:text-[#ffb800]/80 hover:bg-[#ffb800]/10 hover:border-[#ffb800]/30 active:scale-95 transition-all shrink-0 cursor-pointer h-8 w-8 flex items-center justify-center"
              title="Reset Session Stats"
            >
              <RefreshCw size={12} />
            </button>

            <div className="flex-1 flex bg-[#151a22] border border-white/5 rounded-xl p-0.5 h-8 items-center">
              <button
                onClick={() => setActiveView('chart')}
                className={`flex-1 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all duration-200 ${
                  activeView === 'chart' ? 'bg-[#ffb800] text-black shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Chart
              </button>
              <button
                onClick={() => setActiveView('history')}
                className={`flex-1 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all duration-200 ${
                  activeView === 'history' ? 'bg-[#ffb800] text-black shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Runs
              </button>
            </div>
          </div>
          <div className="mt-1 mb-2 flex-1 min-h-[200px] flex flex-col overflow-y-auto custom-scrollbar">
            {activeView === 'chart' ? (
              <VerticalRiskChart
                startBalance={metrics.startBalance}
                currentBalance={currentBalance}
                takeProfitTarget={metrics.takeProfitTarget}
                maxDrawdownLimit={metrics.maxDrawdownLimit}
                height={350}
              />
            ) : (
              <MiniTradeRunHistory
                tradeRuns={tradeRuns}
                currentTradeRun={currentTradeRun}
                onCycleTradeResult={handleCycleTradeResult}
              />
            )}
          </div>

          <div className="grid grid-cols-2 gap-2">
            <StatCard label="Win Rate" value={totalTrades > 0 ? `${winRate.toFixed(0)}%` : '—'} />
            <StatCard label="Trades" value={totalTrades > 0 ? totalTrades : '—'} />
          </div>


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

function ActionMetricCard({ label, value, tone = 'slate', icon: Icon, actionLabel, onAction, disabled = false }) {
  const toneClasses = {
    emerald: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-400 hover:bg-emerald-400/20 hover:border-emerald-400/40',
    rose: 'border-red-400/20 bg-red-400/10 text-red-400 hover:bg-red-400/20 hover:border-red-400/40',
    slate: 'border-white/5 bg-white/5 text-[#e3e6e7] hover:bg-white/10',
  };

  return (
    <button 
      disabled={disabled} 
      onClick={onAction} 
      className={`relative group flex flex-col text-left rounded-xl border px-3 py-2 transition-all duration-200 cursor-pointer disabled:cursor-not-allowed disabled:opacity-45 overflow-hidden ${toneClasses[tone]}`}
    >
      <div className="flex items-center justify-between w-full text-[10px] uppercase tracking-[0.18em] transition-opacity group-hover:opacity-20">
        <div className="flex items-center gap-1.5 opacity-70">
          {Icon && <Icon size={10} />}
          {label}
        </div>
      </div>
      <div className="flex items-end justify-between w-full mt-1 transition-opacity group-hover:opacity-20">
        <span className="text-sm font-bold tracking-tight">{value}</span>
        {actionLabel && (
          <span className={`text-[10px] font-black tracking-widest ${
            tone === 'emerald' ? 'text-emerald-400' : 'text-red-400'
          }`}>
            {actionLabel}
          </span>
        )}
      </div>
      
      {/* Directional Arrow Icons on hover */}
      {!disabled && (
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none bg-black/25">
          {tone === 'emerald' ? (
            <ArrowUp size={28} className="text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.6)] animate-bounce" style={{ animationDuration: '1s' }} />
          ) : tone === 'rose' ? (
            <ArrowDown size={28} className="text-red-400 drop-shadow-[0_0_8px_rgba(248,113,113,0.6)] animate-bounce" style={{ animationDuration: '1s' }} />
          ) : null}
        </div>
      )}
    </button>
  );
}
