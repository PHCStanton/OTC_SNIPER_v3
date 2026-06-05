/**
 * RightSidebar — collapsible info/risk panel.
 * Shows session risk summary and AI assistant tabs when expanded.
 */
import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, TrendingUp, TrendingDown, Minus, Activity, Target } from 'lucide-react';
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
              <Activity size={14} className="text-[#f5df19]" />
              <span className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#f5df19]">Session Risk</span>
            </div>

            <div className="flex bg-[#151a22] border border-white/5 rounded-lg p-0.5">
              <button
                onClick={() => setActiveView('chart')}
                className={`px-2 py-0.5 rounded text-[8px] font-bold uppercase transition-colors ${
                  activeView === 'chart' ? 'bg-[#f5df19] text-black' : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                Chart
              </button>
              <button
                onClick={() => setActiveView('history')}
                className={`px-2 py-0.5 rounded text-[8px] font-bold uppercase transition-colors ${
                  activeView === 'history' ? 'bg-[#f5df19] text-black' : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                Runs
              </button>
            </div>
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
    <button disabled={disabled} onClick={onAction} className={`flex flex-col text-left rounded-xl border px-3 py-2 transition-colors duration-200 cursor-pointer disabled:cursor-not-allowed disabled:opacity-45 ${toneClasses[tone]}`}>
      <div className="flex items-center justify-between w-full text-[10px] uppercase tracking-[0.18em]">
        <div className="flex items-center gap-1.5 opacity-70">
          {Icon && <Icon size={10} />}
          {label}
        </div>
      </div>
      <div className="flex items-end justify-between w-full mt-1">
        <span className="text-sm font-bold tracking-tight">{value}</span>
        {actionLabel && (
          <span className={`text-[10px] font-black tracking-widest ${
            tone === 'emerald' ? 'text-emerald-400' : 'text-red-400'
          }`}>
            {actionLabel}
          </span>
        )}
      </div>
    </button>
  );
}
