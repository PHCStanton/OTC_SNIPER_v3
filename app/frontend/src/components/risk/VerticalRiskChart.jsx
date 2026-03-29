import { TrendingUp, TrendingDown, Target } from 'lucide-react';

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export default function VerticalRiskChart({
  startBalance,
  currentBalance,
  takeProfitTarget,
  maxDrawdownLimit,
  height = 420,
}) {
  const upper = Math.max(startBalance, takeProfitTarget, currentBalance);
  const lower = Math.min(startBalance, maxDrawdownLimit, currentBalance);
  const range = Math.max(1, upper - lower);

  const padding = 36;
  const usableHeight = Math.max(1, height - padding * 2);
  const width = 240;

  const scaleY = (value) => {
    const ratio = (value - lower) / range;
    return padding + usableHeight - (clamp(ratio, 0, 1) * usableHeight);
  };

  const startY = scaleY(startBalance);
  const targetY = scaleY(takeProfitTarget);
  const limitY = scaleY(maxDrawdownLimit);
  const currentY = scaleY(currentBalance);
  const barWidth = 44;
  const barTop = Math.min(startY, currentY);
  const barBottom = Math.max(startY, currentY);
  const barHeight = Math.max(10, barBottom - barTop);
  const barX = (width - barWidth) / 2;

  const isProfit = currentBalance >= startBalance;

  return (
    <div className="rounded-2xl border border-white/5 bg-[#0f1419] p-4 shadow-[0_10px_30px_rgba(0,0,0,0.25)]">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.26em] text-gray-500">Session Visualizer</p>
          <p className="mt-1 text-sm font-semibold text-[#e3e6e7]">Balance, target, and drawdown envelope</p>
        </div>
        <div className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${isProfit ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-400' : 'border-red-400/20 bg-red-400/10 text-red-400'}`}>
          {isProfit ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
          {isProfit ? 'Above baseline' : 'Below baseline'}
        </div>
      </div>

      <div className="relative rounded-2xl border border-white/5 bg-[#0b0f13] p-3">
        <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="100%" className="overflow-visible">
          <defs>
            <linearGradient id="risk-bar" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.95" />
              <stop offset="100%" stopColor="#059669" stopOpacity="0.85" />
            </linearGradient>
            <linearGradient id="risk-loss-bar" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#b91c1c" stopOpacity="0.85" />
            </linearGradient>
          </defs>

          <rect x={16} y={targetY - 1} width={width - 32} height={Math.max(1, startY - targetY)} fill="#10b981" opacity="0.06" />
          <rect x={16} y={startY} width={width - 32} height={Math.max(1, limitY - startY)} fill="#ef4444" opacity="0.06" />

          <line x1={16} y1={targetY} x2={width - 16} y2={targetY} stroke="#10b981" strokeDasharray="6 5" strokeWidth="2" />
          <line x1={16} y1={startY} x2={width - 16} y2={startY} stroke="#64748b" strokeWidth="2" />
          <line x1={16} y1={limitY} x2={width - 16} y2={limitY} stroke="#ef4444" strokeDasharray="6 5" strokeWidth="2" />

          <rect
            x={barX}
            y={barTop}
            width={barWidth}
            height={barHeight}
            rx="6"
            fill={isProfit ? 'url(#risk-bar)' : 'url(#risk-loss-bar)'}
            opacity="0.95"
          />

          <circle cx={barX + barWidth / 2} cy={currentY} r="5" fill={isProfit ? '#10b981' : '#ef4444'} />

          <g>
            <text x={width - 10} y={targetY - 6} fill="#10b981" fontSize="11" fontWeight="700" textAnchor="end">
              Take Profit
            </text>
            <text x={width - 10} y={targetY + 10} fill="#10b981" fontSize="10" textAnchor="end" opacity="0.85">
              ${takeProfitTarget.toFixed(2)}
            </text>
          </g>

          <g>
            <text x={width - 10} y={startY - 6} fill="#94a3b8" fontSize="11" fontWeight="700" textAnchor="end">
              Starting Balance
            </text>
            <text x={width - 10} y={startY + 10} fill="#94a3b8" fontSize="10" textAnchor="end" opacity="0.85">
              ${startBalance.toFixed(2)}
            </text>
          </g>

          <g>
            <text x={width - 10} y={limitY - 6} fill="#ef4444" fontSize="11" fontWeight="700" textAnchor="end">
              Max Drawdown
            </text>
            <text x={width - 10} y={limitY + 10} fill="#ef4444" fontSize="10" textAnchor="end" opacity="0.85">
              ${maxDrawdownLimit.toFixed(2)}
            </text>
          </g>

          <g>
            <text x={barX + barWidth / 2} y={currentY - 12} fill="#e5e7eb" fontSize="12" fontWeight="800" textAnchor="middle">
              ${currentBalance.toFixed(2)}
            </text>
            <text x={barX + barWidth / 2} y={currentY + 20} fill="#94a3b8" fontSize="10" textAnchor="middle">
              Current
            </text>
          </g>
        </svg>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">
        <MetricLabel label="To Target" value={`$${Math.max(0, takeProfitTarget - currentBalance).toFixed(2)}`} tone="emerald" icon={Target} />
        <MetricLabel label="To Limit" value={`$${Math.max(0, currentBalance - maxDrawdownLimit).toFixed(2)}`} tone="rose" icon={Target} />
      </div>
    </div>
  );
}

function MetricLabel({ label, value, tone = 'slate', icon: Icon }) {
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