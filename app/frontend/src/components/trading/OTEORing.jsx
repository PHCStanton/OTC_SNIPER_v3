/**
 * OTEORing — circular confidence indicator used in the Phase 5 trading workspace.
 */
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { formatAssetLabel, getSignalConfidence, getSignalDirection, getSignalLabel } from './chartUtils.js';

function toTitleCase(value) {
  return String(value ?? '')
    .replaceAll('_', ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getManipulationLabels(manipulation) {
  if (!manipulation || typeof manipulation !== 'object') return [];

  const flags = manipulation.flags && typeof manipulation.flags === 'object'
    ? manipulation.flags
    : manipulation;

  const labels = Object.entries(flags)
    .filter(([, active]) => Boolean(active))
    .map(([key]) => {
      if (key === 'push_snap') return 'Push & Snap';
      if (key === 'pinning') return 'Pinning';
      return toTitleCase(key);
    });

  if (labels.length > 0) return labels;
  if (manipulation.type) return [toTitleCase(manipulation.type)];
  return [];
}

function getConfluenceItems(signal, direction) {
  if (!signal || typeof signal !== 'object') return [];

  const marketContext = signal.market_context && typeof signal.market_context === 'object'
    ? signal.market_context
    : {};

  const items = [];
  const velocity = Number(signal.velocity ?? 0);
  const pressurePct = Number(signal.pressure_pct ?? 0);
  const zScore = Number(signal.z_score ?? 0);
  const maturity = Number(signal.maturity ?? 0);
  const level2Adjustment = Number(signal.level2_score_adjustment ?? 0);

  if (direction === 'call' && velocity < 0) items.push('Sell Exhaustion');
  if (direction === 'put' && velocity > 0) items.push('Buy Exhaustion');
  if (Math.abs(zScore) >= 0.35) items.push(`Z-Score ${zScore > 0 ? 'High' : 'Low'}`);
  if (Math.abs(pressurePct) >= 12) items.push(`Pressure ${pressurePct > 0 ? 'Up' : 'Down'}`);
  if (signal.trend_aligned) items.push('Trend Aligned');
  if (direction === 'call' && marketContext.support_alignment) items.push('Support Align');
  if (direction === 'put' && marketContext.resistance_alignment) items.push('Resistance Align');
  if (marketContext.reversal_friendly) items.push('Reversal Friendly');
  if (marketContext.cci_state) items.push(`CCI ${toTitleCase(marketContext.cci_state)}`);
  if (marketContext.adx_regime) items.push(`ADX ${toTitleCase(marketContext.adx_regime)}`);
  if (maturity >= 0.5) items.push(`Maturity ${Math.round(maturity * 100)}%`);
  if (signal.level2_enabled && level2Adjustment !== 0) items.push(`L2 ${level2Adjustment > 0 ? '+' : ''}${level2Adjustment.toFixed(1)}`);
  if (signal.actionable) items.push('Actionable');

  return items.slice(0, 8);
}

export default function OTEORing({ asset, signal, manipulation = null, warmup = false }) {
  const confidence = warmup ? 0 : getSignalConfidence(signal);
  const direction = getSignalDirection(signal);
  const label = getSignalLabel(signal);
  const size = 300;
  const strokeWidth = 24;
  const center = size / 2;
  const radius = center - strokeWidth;
  const circumference = 2 * Math.PI * radius;
  const arcLength = 0.85 * circumference;
  const gapLength = circumference - arcLength;
  const fillLength = (confidence / 100) * arcLength;
  const isPut = direction === 'put';
  const isCall = direction === 'call';
  const isNeutral = !isCall && !isPut;
  const manipulationLabels = warmup ? [] : getManipulationLabels(manipulation);
  const confluenceItems = warmup ? [] : getConfluenceItems(signal, direction);

  const glowColor = warmup
    ? 'rgba(100,116,139,0.2)'
    : isPut
      ? 'rgba(254,116,83,0.4)'
      : isCall
        ? 'rgba(16,185,129,0.4)'
        : 'rgba(59,130,246,0.45)';

  const accentClass = warmup
    ? 'text-slate-400'
    : isPut
      ? 'text-[#fe7453]'
      : isCall
        ? 'text-emerald-500'
        : 'text-blue-400';

  const stroke = warmup
    ? 'url(#warmupGradient)'
    : isPut
      ? 'url(#putGradient)'
      : isCall
        ? 'url(#callGradient)'
        : 'url(#neutralGradient)';

  const rotation = 117;

  return (
    <div className="flex h-full flex-col items-center justify-center py-4">
      <div className="text-center">
        <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-500">Focused Asset</p>
        <p className="mt-1 text-sm font-black tracking-tight text-[#e3e6e7]">{formatAssetLabel(asset)}</p>
      </div>
      <div className="relative mt-3 flex h-64 w-64 items-center justify-center sm:h-72 sm:w-72">
        <svg 
          className="h-full w-full" 
          viewBox={`0 0 ${size} ${size}`}
          style={{ 
            filter: `drop-shadow(0 0 10px ${glowColor}) drop-shadow(0 0 20px ${glowColor})`,
            transform: `rotate(${rotation}deg)` 
          }}
        >
          <defs>
            <linearGradient id="putGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fe7453" />
              <stop offset="100%" stopColor="#f5df19" />
            </linearGradient>
            <linearGradient id="callGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#34d399" />
            </linearGradient>
            <linearGradient id="neutralGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#60a5fa" />
            </linearGradient>
            <linearGradient id="warmupGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#475569" />
              <stop offset="100%" stopColor="#64748b" />
            </linearGradient>
          </defs>

          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="transparent"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${gapLength}`}
            strokeLinecap="round"
            className="text-white/5"
          />

          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="transparent"
            stroke={stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={`${fillLength} ${circumference}`}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-5xl sm:text-7xl font-black tracking-tighter ${accentClass}`}>
            {warmup ? '—' : `${Math.round(confidence)}%`}
          </span>
          <span className="mt-2 text-xs font-bold uppercase tracking-[0.2em] text-gray-500">
            {warmup ? 'Warming up' : isPut ? 'Sell Pressure' : isCall ? 'Buy Pressure' : 'Neutral State'}
          </span>
        </div>
      </div>

      {!warmup && (
        <>
          <div className="mt-6 flex items-center gap-2 rounded-full border border-white/5 bg-[#1a1717]/80 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.15em] text-gray-300 shadow-lg backdrop-blur">
            {isPut ? (
              <ArrowDownRight size={14} className="text-[#fe7453]" />
            ) : isCall ? (
              <ArrowUpRight size={14} className="text-emerald-400" />
            ) : (
              <Minus size={14} className="text-blue-400" />
            )}
            <span className={accentClass}>{label}</span>
          </div>
          <div className="mt-4 flex w-full max-w-xl flex-col gap-3">
            <div className="rounded-2xl border border-white/5 bg-[#1a1717]/80 px-4 py-3 backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-gray-500">Manipulation</span>
                <span className={`text-[10px] font-bold uppercase tracking-[0.18em] ${manipulationLabels.length > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {manipulationLabels.length > 0 ? 'Flagged' : 'Clear'}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {(manipulationLabels.length > 0 ? manipulationLabels : ['No Active Flags']).map((item) => (
                  <span
                    key={item}
                    className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] ${manipulationLabels.length > 0 ? 'border border-rose-500/20 bg-rose-500/10 text-rose-300' : 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-300'}`}
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-white/5 bg-[#1a1717]/80 px-4 py-3 backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-gray-500">Confluences</span>
                <span className={`text-[10px] font-bold uppercase tracking-[0.18em] ${isPut ? 'text-[#fe7453]' : isCall ? 'text-emerald-400' : 'text-blue-400'}`}>
                  {direction ? direction.toUpperCase() : 'NEUTRAL'}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {(confluenceItems.length > 0 ? confluenceItems : ['No Strong Alignment']).map((item) => (
                  <span
                    key={item}
                    className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] ${isPut ? 'border border-[#fe7453]/20 bg-[#fe7453]/10 text-[#ffb19f]' : isCall ? 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-300' : 'border border-blue-500/20 bg-blue-500/10 text-blue-300'}`}
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
