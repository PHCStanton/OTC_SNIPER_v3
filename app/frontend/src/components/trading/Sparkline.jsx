/**
 * Sparkline — live tick chart panel used in the Phase 5 trading workspace.
 */
import { useMemo } from 'react';
import { Activity, ArrowDownRight, ArrowUpRight, BarChart3, Layers3 } from 'lucide-react';
import {
  buildChartPoints,
  extractNumericSeries,
  formatAssetLabel,
  formatPrice,
  getSignalConfidence,
  getSignalDirection,
  getSignalLabel,
  getTrendPercent,
  pointsToPath,
} from './chartUtils.js';

export default function Sparkline({ asset, ticks, signal, warmup = false, className = '' }) {
  const series = useMemo(() => extractNumericSeries(ticks), [ticks]);
  const points = useMemo(() => buildChartPoints(series), [series]);
  const path = useMemo(() => pointsToPath(points), [points]);
  const latest = series.length > 0 ? series[series.length - 1] : null;
  const trend = getTrendPercent(series);
  const signalConfidence = getSignalConfidence(signal);
  const signalDirection = getSignalDirection(signal);
  const signalLabel = getSignalLabel(signal);
  const trendUp = trend >= 0;

  return (
    <section className={`relative overflow-hidden rounded-xl border border-white/5 bg-[#212127] shadow-2xl shadow-black/30 backdrop-blur ${className}`}>
      <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-r from-[#f5df19]/10 via-transparent to-[#f2892c]/10" />

      <div className="relative flex items-center justify-between gap-3 border-b border-white/5 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#1a1717] text-[#f5df19]">
            <BarChart3 size={17} />
          </div>

          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-400">Live chart</p>
            <h2 className="text-lg font-black tracking-tight text-[#e3e6e7]">
              {formatAssetLabel(asset)}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-gray-400">
          <span className="rounded-full border border-white/5 bg-[#1a1717] px-2.5 py-1 text-[#e3e6e7]">
            30s
          </span>
          <span className="rounded-full border border-white/5 bg-[#1a1717] px-2.5 py-1 text-[#e3e6e7]">
            1m
          </span>
          <span className="rounded-full border border-white/5 bg-[#f5df19] px-2.5 py-1 text-[#615700]">
            5m
          </span>
        </div>
      </div>

      {series.length === 0 ? (
        <div className="flex min-h-[390px] flex-col items-center justify-center gap-3 px-6 py-10 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/5 bg-[#1a1717] text-[#f5df19]">
            <Activity size={22} />
          </div>
          <div>
            <p className="text-base font-semibold text-[#e3e6e7]">Awaiting tick stream</p>
            <p className="mt-1 text-sm text-gray-400">
              {warmup ? 'Warmup is still in progress for this asset.' : 'Select an asset and wait for live market data.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="relative min-h-[390px] px-4 pb-4 pt-10">
          <div className="absolute left-4 top-4 z-10 rounded-2xl border border-white/10 bg-[#1a1717]/90 px-3 py-2 shadow-2xl backdrop-blur-md">
            <div className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${trendUp ? 'bg-emerald-400' : 'bg-[#fe7453]'}`} />
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-gray-500">Signal</p>
                <p className="text-xs font-bold text-[#e3e6e7]">{signalLabel}</p>
              </div>
            </div>
            <div className="mt-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-400">
              <span className={signalDirection === 'put' ? 'text-[#fe7453]' : 'text-emerald-400'}>{signalDirection === 'call' ? 'CALL' : signalDirection === 'put' ? 'PUT' : 'NEUTRAL'}</span>
              <span className="text-gray-600">•</span>
              <span className="text-[#f5df19]">{Math.round(signalConfidence)}%</span>
            </div>
          </div>

          <svg className="h-[330px] w-full drop-shadow-[0_0_12px_rgba(255,237,109,0.18)]" viewBox="0 0 1000 360" role="img" aria-label={`${formatAssetLabel(asset)} live sparkline`}>
            <defs>
              <linearGradient id="sparklineLine" x1="0%" x2="100%" y1="0%" y2="0%">
                <stop offset="0%" stopColor="#ffed6d" />
                <stop offset="55%" stopColor="#f2892c" />
                <stop offset="100%" stopColor="#e6d000" />
              </linearGradient>
              <linearGradient id="sparklineGlow" x1="0%" x2="0%" y1="0%" y2="100%">
                <stop offset="0%" stopColor="rgba(255,237,109,0.22)" />
                <stop offset="100%" stopColor="rgba(255,237,109,0)" />
              </linearGradient>
            </defs>

            {[90, 180, 270].map((y) => (
              <line
                key={y}
                x1="0"
                x2="1000"
                y1={y}
                y2={y}
                stroke="currentColor"
                strokeOpacity="0.06"
                className="text-slate-500"
              />
            ))}

            {path && (
              <>
                <path d={`${path} L 972 332 L 28 332 Z`} fill="url(#sparklineGlow)" opacity="0.9" />
                <path d={path} fill="none" stroke="url(#sparklineLine)" strokeWidth="4" strokeLinejoin="round" strokeLinecap="round" />
              </>
            )}

            {points.map((point, index) => (
              <circle
                key={`${point.x}-${point.y}-${index}`}
                cx={point.x}
                cy={point.y}
                r={index === points.length - 1 ? 6 : 3}
                fill={index === points.length - 1 ? '#ffed6d' : '#f2892c'}
                opacity={index === points.length - 1 ? 1 : 0.65}
              />
            ))}
          </svg>

          {latest !== null && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2 rounded-xl border border-[#f5df19]/30 bg-[#f5df19] px-3 py-2 text-right shadow-lg shadow-black/30">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#584f00]/70">Last price</p>
              <p className="text-lg font-black leading-none text-[#584f00]">{formatPrice(latest)}</p>
            </div>
          )}

          <div className="absolute bottom-4 left-4 flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-400">
            <span className="flex items-center gap-1.5 rounded-full border border-white/5 bg-[#1a1717] px-2.5 py-1 text-[#e3e6e7]">
              {trendUp ? <ArrowUpRight size={11} className="text-emerald-400" /> : <ArrowDownRight size={11} className="text-[#fe7453]" />}
              {trendUp ? '+' : ''}{trend.toFixed(2)}%
            </span>
            <span className="flex items-center gap-1.5 rounded-full border border-white/5 bg-[#1a1717] px-2.5 py-1 text-[#e3e6e7]">
              <Layers3 size={11} />
              {series.length} ticks
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
