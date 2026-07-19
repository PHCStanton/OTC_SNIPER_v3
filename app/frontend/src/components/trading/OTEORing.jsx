/**
 * OTEORing — circular confidence indicator used in the Phase 5 trading workspace.
 * Manipulation + Confluence data is now rendered via AnalysisTerminal (fixed-height
 * terminal display) instead of dynamic badge sections.
 */
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { formatAssetLabel, getSignalConfidence, getSignalDirection, getSignalLabel } from './chartUtils.js';
import AnalysisTerminal from './AnalysisTerminal.jsx';

/**
 * Color classes for each Level 3 regime label (maps Market_Regimes.md taxonomy).
 * - Green  → ideal conditions for OTEO reversals
 * - Yellow → conditional (trend-aligned entries only)
 * - Orange → dangerous (high momentum or breakout)
 * - Red    → avoid entirely
 * - Gray   → insufficient data
 */
const REGIME_STYLES = {
  RANGE_BOUND:       { text: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/10', label: 'Range Bound' },
  TREND_REVERSAL:    { text: 'text-green-400',   border: 'border-green-500/30',   bg: 'bg-green-500/10',   label: 'Trend Reversal' },
  TREND_PULLBACK:    { text: 'text-yellow-400',  border: 'border-yellow-500/30',  bg: 'bg-yellow-500/10',  label: 'Trend Pullback' },
  STRONG_MOMENTUM:   { text: 'text-orange-400',  border: 'border-orange-500/30',  bg: 'bg-orange-500/10',  label: 'Strong Momentum' },
  BREAKOUT:          { text: 'text-amber-400',   border: 'border-amber-500/30',   bg: 'bg-amber-500/10',   label: 'Breakout' },
  CHOPPY:            { text: 'text-red-400',     border: 'border-red-500/30',     bg: 'bg-red-500/10',     label: 'Choppy' },
  INSUFFICIENT_DATA: { text: 'text-gray-500',    border: 'border-gray-600/30',    bg: 'bg-gray-500/5',     label: 'Insufficient Data' },
};

const getVolatilityClass = (score) => {
  if (score < 30) return { label: 'LOW', color: '#10b981', textClass: 'text-emerald-400', glow: 'rgba(16, 185, 129, 0.4)' };
  if (score < 70) return { label: 'MED', color: '#f5df19', textClass: 'text-yellow-400', glow: 'rgba(245, 223, 25, 0.4)' };
  return { label: 'HIGH', color: '#ef4444', textClass: 'text-red-500', glow: 'rgba(239, 68, 68, 0.4)' };
};

const getLiquidityClass = (score) => {
  if (score < 30) return { label: 'LOW', color: '#ef4444', textClass: 'text-red-500', glow: 'rgba(239, 68, 68, 0.4)' };
  if (score < 70) return { label: 'MED', color: '#f5df19', textClass: 'text-yellow-400', glow: 'rgba(245, 223, 25, 0.4)' };
  return { label: 'HIGH', color: '#06b6d4', textClass: 'text-cyan-400', glow: 'rgba(6, 182, 212, 0.4)' };
};

export default function OTEORing({ asset, signal, manipulation = null, warmup = false }) {
  const volScore = warmup ? 0 : (signal?.market_context?.volatility_score ?? 0);
  const liqScore = warmup ? 0 : (signal?.market_context?.liquidity_score ?? 0);
  const volStyle = getVolatilityClass(volScore);
  const liqStyle = getLiquidityClass(liqScore);
  const confidence = warmup ? 0 : getSignalConfidence(signal);

  const direction  = getSignalDirection(signal);
  const label      = getSignalLabel(signal);
  const size        = 300;
  const strokeWidth = 24;
  const center      = size / 2;
  const radius      = center - strokeWidth;
  const circumference = 2 * Math.PI * radius;
  const arcLength     = 0.85 * circumference;
  const gapLength     = circumference - arcLength;
  const fillLength    = (confidence / 100) * arcLength;
  const isPut    = direction === 'put';
  const isCall   = direction === 'call';
  const isNeutral = !isCall && !isPut;

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
            transform: `rotate(${rotation}deg)`,
          }}
        >
          <defs>
            <linearGradient id="putGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%"   stopColor="#fe7453" />
              <stop offset="100%" stopColor="#f5df19" />
            </linearGradient>
            <linearGradient id="callGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%"   stopColor="#10b981" />
              <stop offset="100%" stopColor="#34d399" />
            </linearGradient>
            <linearGradient id="neutralGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%"   stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#60a5fa" />
            </linearGradient>
            <linearGradient id="warmupGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%"   stopColor="#475569" />
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

      {/* Direction label pill with Volatility & Liquidity half-gauges */}
      {!warmup && (
        <div className="mt-6 flex w-full max-w-sm items-center justify-between px-4">
          {/* Volatility Half-Gauge */}
          <div className="flex flex-col items-center">
            <div className="relative h-8 w-16">
              <svg className="w-full h-full" viewBox="0 0 64 32">
                <path
                  d="M 8 30 A 24 24 0 0 1 56 30"
                  fill="none"
                  stroke="rgba(255,255,255,0.05)"
                  strokeWidth="5"
                  strokeLinecap="round"
                />
                <path
                  d="M 8 30 A 24 24 0 0 1 56 30"
                  fill="none"
                  stroke={volStyle.color}
                  strokeWidth="5"
                  strokeLinecap="round"
                  strokeDasharray="75.4"
                  strokeDashoffset={75.4 - (volScore / 100) * 75.4}
                  className="transition-all duration-1000 ease-out"
                  style={{ filter: `drop-shadow(0 0 4px ${volStyle.glow})` }}
                />
              </svg>
              <div className="absolute inset-0 flex items-end justify-center pb-1">
                <span className={`text-[10px] font-black ${volStyle.textClass}`}>{Math.round(volScore)}%</span>
              </div>
            </div>
            <span className={`mt-1 text-[9px] font-black uppercase tracking-[0.1em] ${volStyle.textClass}`}>Vol • {volStyle.label}</span>
          </div>

          {/* Direction Pill */}
          <div className="flex items-center gap-2 rounded-full border border-white/5 bg-[#1a1717]/80 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.15em] text-gray-300 shadow-lg backdrop-blur">
            {isPut ? (
              <ArrowDownRight size={14} className="text-[#fe7453]" />
            ) : isCall ? (
              <ArrowUpRight size={14} className="text-emerald-400" />
            ) : (
              <Minus size={14} className="text-blue-400" />
            )}
            <span className={accentClass}>{label}</span>
          </div>

          {/* Liquidity Half-Gauge */}
          <div className="flex flex-col items-center">
            <div className="relative h-8 w-16">
              <svg className="w-full h-full" viewBox="0 0 64 32">
                <path
                  d="M 8 30 A 24 24 0 0 1 56 30"
                  fill="none"
                  stroke="rgba(255,255,255,0.05)"
                  strokeWidth="5"
                  strokeLinecap="round"
                />
                <path
                  d="M 8 30 A 24 24 0 0 1 56 30"
                  fill="none"
                  stroke={liqStyle.color}
                  strokeWidth="5"
                  strokeLinecap="round"
                  strokeDasharray="75.4"
                  strokeDashoffset={75.4 - (liqScore / 100) * 75.4}
                  className="transition-all duration-1000 ease-out"
                  style={{ filter: `drop-shadow(0 0 4px ${liqStyle.glow})` }}
                />
              </svg>
              <div className="absolute inset-0 flex items-end justify-center pb-1">
                <span className={`text-[10px] font-black ${liqStyle.textClass}`}>{Math.round(liqScore)}%</span>
              </div>
            </div>
            <span className={`mt-1 text-[9px] font-black uppercase tracking-[0.1em] ${liqStyle.textClass}`}>Liq • {liqStyle.label}</span>
          </div>
        </div>
      )}


      {/* Level 3 Regime Badge — shown when L3 is enabled and regime is classified */}
      {!warmup && signal?.level3_enabled && signal?.regime_label && (
        (() => {
          const rs = REGIME_STYLES[signal.regime_label] || REGIME_STYLES.INSUFFICIENT_DATA;
          return (
            <div
              className={`mt-2 flex items-center gap-1.5 rounded-full border ${rs.border} ${rs.bg} px-3 py-1 text-[10px] font-mono font-semibold uppercase tracking-wider ${rs.text} transition-colors duration-500`}
              title={`L3 Regime: ${signal.regime_label} — Confidence: ${signal.regime_confidence}%`}
            >
              <span>{rs.label}</span>
              <span className="opacity-60">{signal.regime_stable ? '✓' : '~'}</span>
              {signal.regime_confidence > 0 && (
                <span className="opacity-50">{signal.regime_confidence}%</span>
              )}
            </div>
          );
        })()
      )}

      {/* Fixed-height terminal — replaces the dynamic badge sections */}
      <div className="mt-4 w-full max-w-xl">
        <AnalysisTerminal
          signal={signal}
          manipulation={manipulation}
          direction={direction}
          warmup={warmup}
        />
      </div>
    </div>
  );
}
