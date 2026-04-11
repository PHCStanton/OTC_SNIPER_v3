/**
 * Sparkline — live tick chart panel used in the Phase 5 trading workspace.
 */
import { useMemo, useCallback } from 'react';
import { Activity, ArrowDownRight, ArrowUpRight, BarChart3, Layers3, Ghost, User, Eraser } from 'lucide-react';
import { useStreamStore } from '../../stores/useStreamStore.js';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { soundManager } from '../../utils/soundUtils.js';
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

// Stable fallback — must NOT be defined inline (new [] ref each render = infinite loop)
const EMPTY_MARKERS = Object.freeze([]);

export default function Sparkline({ asset, ticks, signal, warmup = false, className = '' }) {
  const series = useMemo(() => extractNumericSeries(ticks), [ticks]);
  const points = useMemo(() => buildChartPoints(series), [series]);
  const path = useMemo(() => pointsToPath(points), [points]);
  const { latest, trend, trendUp, signalConfidence, signalDirection, signalLabel } = useMemo(() => {
    const t = getTrendPercent(series);
    return {
      latest: series.length > 0 ? series[series.length - 1] : null,
      trend: t,
      trendUp: t >= 0,
      signalConfidence: getSignalConfidence(signal),
      signalDirection: getSignalDirection(signal),
      signalLabel: getSignalLabel(signal),
    };
  }, [series, signal]);

  const showGhostMarkers = useSettingsStore((s) => s.showGhostEntryMarkers);
  const showLiveMarkers = useSettingsStore((s) => s.showLiveEntryMarkers);
  // Setters are stable singletons — read from getState() inside handlers to avoid render loops
  const handleToggleGhostMarkers = useCallback(() =>
    useSettingsStore.getState().setShowGhostEntryMarkers(!useSettingsStore.getState().showGhostEntryMarkers), []);
  const handleToggleLiveMarkers = useCallback(() =>
    useSettingsStore.getState().setShowLiveEntryMarkers(!useSettingsStore.getState().showLiveEntryMarkers), []);
  const handleClearMarkers = useCallback(() => {
    useStreamStore.getState().clearMarkers(asset);
    soundManager.playClick();
  }, [asset]);
  const allMarkers = useStreamStore((s) => s.tradeMarkers[asset] ?? EMPTY_MARKERS);

  const activeMarkers = useMemo(() => {
    return allMarkers.filter(m => (m.kind === 'ghost' && showGhostMarkers) || (m.kind !== 'ghost' && showLiveMarkers));
  }, [allMarkers, showGhostMarkers, showLiveMarkers]);

  const priceToY = useMemo(() => {
    if (series.length === 0) return () => 0;
    let min = series[0];
    let max = series[0];
    for (let i = 1; i < series.length; i++) {
        if (series[i] < min) min = series[i];
        if (series[i] > max) max = series[i];
    }
    const range = max - min || 1;
    const padding = 28;
    const height = 360;
    const usableHeight = Math.max(1, height - padding * 2);
    return (price) => padding + usableHeight - ((price - min) / range) * usableHeight;
  }, [series]);

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
          <button 
            onClick={handleToggleGhostMarkers}
            aria-label="Toggle ghost trade markers"
            aria-pressed={showGhostMarkers}
            className={`flex items-center gap-1 rounded-full border px-2 py-1 transition-colors ${showGhostMarkers ? 'border-[#f5df19]/30 bg-[#f5df19]/10 text-[#f5df19]' : 'border-white/5 bg-[#1a1717] text-gray-500'}`}>
            <Ghost size={11} /> Markers
          </button>
          <button 
            onClick={handleToggleLiveMarkers}
            aria-label="Toggle live trade markers"
            aria-pressed={showLiveMarkers}
            className={`flex items-center gap-1 rounded-full border px-2 py-1 transition-colors ${showLiveMarkers ? 'border-sky-400/30 bg-sky-400/10 text-sky-400' : 'border-white/5 bg-[#1a1717] text-gray-500'}`}>
            <User size={11} /> Markers
          </button>
          
          <div className="h-4 w-px bg-white/10 mx-1" />

          <button 
            onClick={handleClearMarkers}
            title="Clear all markers for this asset"
            className="flex items-center gap-1 rounded-full border border-white/5 bg-[#1a1717] px-2 py-1 text-gray-500 transition-colors hover:border-red-500/30 hover:bg-red-500/10 hover:text-red-400">
            <Eraser size={11} /> Clear
          </button>
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
              <span className={`h-2.5 w-2.5 rounded-full ${signalDirection === 'call' ? 'bg-emerald-400' : signalDirection === 'put' ? 'bg-[#fe7453]' : 'bg-gray-500'}`} />
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

            {/* Only render the latest point as a circle to reduce DOM overhead (was 300 circles) */}
            {points.length > 0 && (
              <circle
                cx={points[points.length - 1].x}
                cy={points[points.length - 1].y}
                r={6}
                fill="#ffed6d"
                className="drop-shadow-[0_0_8px_rgba(255,237,109,0.8)]"
              />
            )}

            {activeMarkers.map(m => {
              const y = priceToY(m.entryPrice);
              const isWin = m.outcome === 'win';
              const isLoss = m.outcome === 'loss';
              const color = isWin ? '#34d399' : isLoss ? '#f87171' : '#fbbf24'; // emerald-400, red-400, amber-400
              const isGhost = m.kind === 'ghost';
              
              return (
                <g key={m.tradeId}>
                  <line x1="0" x2="1000" y1={y} y2={y} stroke={color} strokeWidth="1.5" strokeDasharray="6 6" strokeOpacity={isWin || isLoss ? "0.4" : "0.8"} />
                  <text x="12" y={y - 8} fill={color} fontSize="12" fontWeight="bold">
                    {isGhost ? '👻' : '👤'} {(m.direction ?? 'N/A').toUpperCase()}
                  </text>
                  {m.profit != null && (
                    <text x="988" y={y - 8} textAnchor="end" fill={color} fontSize="12" fontWeight="bold">
                       {m.profit > 0 ? '+' : ''}${Math.abs(m.profit).toFixed(2)}
                    </text>
                  )}
                </g>
              );
            })}
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
