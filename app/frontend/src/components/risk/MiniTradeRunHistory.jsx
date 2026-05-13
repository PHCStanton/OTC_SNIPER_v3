/**
 * MiniTradeRunHistory
 * Compact variant of TradeRunHistory — same data model, stripped visual.
 * Shows: TR# label | W/L/V badge row | PnL value, separated by dividers.
 * No status pills, no trade counts, no descriptive sub-labels.
 */

const OUTCOME = {
  win:  { label: 'W', bg: 'bg-emerald-500/20', border: 'border-emerald-500/30', text: 'text-emerald-400' },
  loss: { label: 'L', bg: 'bg-red-500/20',     border: 'border-red-500/30',     text: 'text-red-400'     },
  void: { label: 'V', bg: 'bg-white/5',         border: 'border-white/10',       text: 'text-gray-400'    },
};

function OutcomeBadge({ outcome, onClick, edited }) {
  const style = OUTCOME[outcome] ?? OUTCOME.void;
  return (
    <button
      type="button"
      onClick={onClick}
      title="Click to cycle WIN → LOSS → VOID"
      className={[
        'inline-flex items-center justify-center',
        'w-9 h-9 rounded-lg border',
        'text-[13px] font-black uppercase',
        'transition-transform hover:scale-105 active:scale-95',
        style.bg, style.border, style.text,
        edited ? 'ring-1 ring-white/10' : '',
      ].join(' ')}
    >
      {style.label}
    </button>
  );
}

export default function MiniTradeRunHistory({ tradeRuns = [], currentTradeRun, onCycleTradeResult }) {
  const allRuns = [...tradeRuns, currentTradeRun].filter((run) => run?.trades);

  if (allRuns.length === 0) {
    return (
      <p className="text-[11px] text-gray-600 italic py-2 text-center">
        No trade runs yet
      </p>
    );
  }

  return (
    <div className="flex flex-col divide-y divide-white/5">
      {allRuns.map((run, index) => {
        // Derive a compact label: "TR 1", "TR 2", etc. — strip the long "Trade Run N" wording
        const shortLabel = run.label
          ? run.label.replace(/trade\s+run\s*/i, 'TR ').trim()
          : `TR ${index + 1}`;

        const pnlPositive = run.pnl >= 0;

        return (
          <div key={run.id} className="py-3 first:pt-0 last:pb-0">
            {/* Row: label left, PnL right */}
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold tracking-[0.2em] text-gray-400 uppercase">
                {shortLabel}
              </span>
              <span className={`text-[12px] font-black tabular-nums ${pnlPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                {pnlPositive ? '+' : ''}${run.pnl.toFixed(2)}
              </span>
            </div>

            {/* Badge row */}
            <div className="flex flex-wrap gap-1.5">
              {run.trades.length === 0 ? (
                <span className="text-[10px] text-gray-600 italic">No trades</span>
              ) : (
                run.trades.map((trade) => (
                  <OutcomeBadge
                    key={trade.id}
                    outcome={trade.outcome}
                    edited={trade.edited}
                    onClick={() => onCycleTradeResult?.(run.id, trade.id, trade.outcome)}
                  />
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
