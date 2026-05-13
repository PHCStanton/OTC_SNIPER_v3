/**
 * OTEORing — circular confidence indicator used in the Phase 5 trading workspace.
 * Manipulation + Confluence data is now rendered via AnalysisTerminal (fixed-height
 * terminal display) instead of dynamic badge sections.
 */
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { formatAssetLabel, getSignalConfidence, getSignalDirection, getSignalLabel } from './chartUtils.js';
import AnalysisTerminal from './AnalysisTerminal.jsx';

export default function OTEORing({ asset, signal, manipulation = null, warmup = false }) {
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

      {/* Direction label pill */}
      {!warmup && (
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
