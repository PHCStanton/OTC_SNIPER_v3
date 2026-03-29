/**
 * OTEORing — circular confidence indicator used in the Phase 5 trading workspace.
 */
import { Activity, ArrowDownRight, ArrowUpRight } from 'lucide-react';
import { formatAssetLabel, getSignalConfidence, getSignalDirection, getSignalLabel } from './chartUtils.js';

export default function OTEORing({ asset, signal, warmup = false }) {
  const confidence = warmup ? 0 : getSignalConfidence(signal);
  const direction = getSignalDirection(signal);
  const label = getSignalLabel(signal);
  const strokeDashoffset = 175.84 - (175.84 * confidence) / 100;

  const ringClass = warmup
    ? 'text-slate-300 dark:text-slate-600'
    : direction === 'put'
      ? 'text-rose-500'
      : 'text-emerald-500';

  const accentClass = warmup
    ? 'text-slate-500 dark:text-slate-400'
    : direction === 'put'
      ? 'text-rose-500'
      : 'text-emerald-500';

  return (
    <section className="flex h-full flex-col items-center justify-between rounded-xl border border-white/5 bg-[#212127] px-4 py-4 text-center shadow-2xl shadow-black/30 backdrop-blur">
      <div className="flex items-center justify-between self-stretch">
        <div className="text-left">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-400">OTEO ring</p>
          <p className="text-sm font-bold text-[#e3e6e7]">{formatAssetLabel(asset)}</p>
        </div>
        <div className={`flex h-9 w-9 items-center justify-center rounded-full border ${warmup ? 'border-white/5 bg-[#1a1717]' : direction === 'put' ? 'border-[#fe7453]/20 bg-[#fe7453]/10' : 'border-emerald-500/20 bg-emerald-500/10'}`}>
          <Activity size={14} className={accentClass} />
        </div>
      </div>

      <div className="relative my-3 h-32 w-32">
        <svg className="h-full w-full -rotate-90">
          <circle cx="64" cy="64" r="28" fill="transparent" stroke="currentColor" strokeWidth="5" className="text-white/5" />
          <circle
            cx="64"
            cy="64"
            r="28"
            fill="transparent"
            stroke="currentColor"
            strokeWidth="5"
            strokeDasharray="175.84"
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className={ringClass}
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <p className={`text-3xl font-black leading-none ${accentClass}`}>{warmup ? '—' : `${Math.round(confidence)}%`}</p>
          <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-gray-400">
            {warmup ? 'warming up' : direction === 'put' ? 'sell pressure' : direction === 'call' ? 'buy pressure' : 'neutral'}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 rounded-full border border-white/5 bg-[#1a1717] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-400">
        {direction === 'put' ? <ArrowDownRight size={11} className="text-[#fe7453]" /> : <ArrowUpRight size={11} className="text-emerald-400" />}
        <span>{label}</span>
      </div>
    </section>
  );
}
