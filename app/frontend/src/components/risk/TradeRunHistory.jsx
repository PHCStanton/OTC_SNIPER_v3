import { ChevronRight, Circle, PencilLine } from 'lucide-react';

const OUTCOME_LABELS = {
  win: { label: 'W', tone: 'border-emerald-400/30 bg-emerald-400/12 text-emerald-400' },
  loss: { label: 'L', tone: 'border-red-400/30 bg-red-400/12 text-red-400' },
  void: { label: 'V', tone: 'border-slate-400/30 bg-slate-400/12 text-slate-300' },
};

export default function TradeRunHistory({ tradeRuns, currentTradeRun, onCycleTradeResult }) {
  const allRuns = [...tradeRuns, currentTradeRun].filter((run) => run && run.trades);

  return (
    <div className="rounded-2xl border border-white/5 bg-[#0f1419] p-4 shadow-[0_10px_30px_rgba(0,0,0,0.22)]">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.26em] text-gray-500">Trade Run History</p>
          <p className="mt-1 text-sm font-semibold text-[#e3e6e7]">WIN / LOSS / VOID badges with override support</p>
        </div>
        <div className="inline-flex items-center gap-1.5 rounded-full border border-white/5 bg-white/5 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">
          <PencilLine size={11} />
          Click a badge to cycle
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {allRuns.length === 0 ? (
          <EmptyState />
        ) : (
          allRuns.map((run, index) => {
            const isCurrent = index === allRuns.length - 1 && !run.completedAt;
            return (
              <section key={run.id} className="rounded-2xl border border-white/5 bg-[#0b0f13] p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${isCurrent ? 'bg-[#f5df19]/10 text-[#f5df19]' : 'bg-white/5 text-gray-400'}`}>
                      {isCurrent ? 'In Progress' : 'Completed'}
                    </span>
                    <h4 className="text-sm font-semibold text-[#e3e6e7]">{run.label}</h4>
                  </div>
                  <div className={`text-sm font-bold ${run.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {run.pnl >= 0 ? '+' : ''}${run.pnl.toFixed(2)}
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  {run.trades.length === 0 ? (
                    <span className="flex items-center gap-1.5 rounded-full border border-dashed border-white/10 px-3 py-1.5 text-[11px] text-gray-500">
                      <Circle size={10} />
                      No trades yet
                    </span>
                  ) : (
                    run.trades.map((trade, tradeIndex) => {
                      const tone = OUTCOME_LABELS[trade.outcome] || OUTCOME_LABELS.void;
                      return (
                        <button
                          key={trade.id}
                          type="button"
                          onClick={() => onCycleTradeResult?.(run.id, trade.id, trade.outcome)}
                          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] transition hover:scale-[1.02] ${tone.tone} ${trade.edited ? 'ring-1 ring-white/10' : ''}`}
                          title="Click to cycle WIN → LOSS → VOID"
                        >
                          {tone.label}
                          <span className="text-[10px] opacity-70">#{tradeIndex + 1}</span>
                          {trade.edited && <PencilLine size={10} />}
                        </button>
                      );
                    })
                  )}
                </div>

                <div className="mt-3 flex items-center justify-between text-[11px] uppercase tracking-[0.16em] text-gray-500">
                  <span>{run.totalTrades || run.trades.length} trades</span>
                  <span>{run.completedAt ? 'Locked' : 'Active'}</span>
                </div>
              </section>
            );
          })
        )}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 bg-[#0b0f13] px-4 py-8 text-center">
      <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl border border-white/5 bg-white/5 text-gray-500">
        <ChevronRight size={18} />
      </div>
      <p className="text-sm font-semibold text-[#e3e6e7]">No trade runs yet</p>
      <p className="mt-1 text-xs text-gray-500">Switch to Manual Mode or wait for live SSID trades to populate the session.</p>
    </div>
  );
}