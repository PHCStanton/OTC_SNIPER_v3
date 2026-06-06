/**
 * Sparkline — live tick chart panel used in the Phase 5 trading workspace.
 * Redesigned to follow the Stitch Design Reference.
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
  const points = useMemo(() => buildChartPoints(series, 1000, 360, 28, 180), [series]);
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

  /**
   * Compute the LAST PRICE tag's vertical position in container-pixel space.
   * Scales the last SVG point's Y (viewBox 0-360) into the 330px rendered SVG,
   * offset by the container's pt-10 (40px) top padding, then clamped so the
   * tag (≈56px tall) never clips the chart boundaries.
   */
  const lastPriceLabelY = useMemo(() => {
    if (points.length === 0) return null;
    const SVG_TOP_PX  = 40;   // pt-10 container padding
    const SVG_H_PX    = 330;  // h-[330px] SVG rendered height
    const SVG_VB_H    = 360;  // viewBox height
    const HALF_TAG_H  = 28;   // ≈ half of the tag's ~56px height
    const dotY = SVG_TOP_PX + (points[points.length - 1].y / SVG_VB_H) * SVG_H_PX;
    return Math.max(SVG_TOP_PX + HALF_TAG_H, Math.min(SVG_TOP_PX + SVG_H_PX - HALF_TAG_H, dotY));
  }, [points]);

  return (
    <section className={`relative overflow-hidden rounded-[20px] border border-white/5 bg-[#1a1c22] shadow-xl ${className}`}>
      <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-r from-[#ffb800]/5 via-transparent to-[#f2892c]/5" />

      <div className="relative flex items-center justify-between gap-3 border-b border-white/5 px-6 py-4 bg-[#25282f]/30">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#25282f] text-[#ffb800] border border-white/5">
            <BarChart3 size={20} />
          </div>

          <div>
            <p className="text-[10px] font-black uppercase tracking-widest text-[#ffb800]">Live Telemetry</p>
            <h2 className="text-md font-black uppercase tracking-wider text-white">
              {formatAssetLabel(asset)}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2 text-[9px] font-black uppercase tracking-widest text-gray-500">
          <button 
            onClick={handleToggleGhostMarkers}
            aria-label="Toggle ghost trade markers"
            aria-pressed={showGhostMarkers}
            className={`flex items-center gap-2 rounded-lg border px-3 py-2 transition-all ${
              showGhostMarkers 
                ? 'border-[#ffb800]/30 bg-[#ffb800]/10 text-[#ffb800]' 
                : 'border-white/5 bg-[#25282f]/30 text-gray-500 hover:text-gray-400'
            }`}
          >
            <Ghost size={11} /> Ghost Markers
          </button>
          <button 
            onClick={handleToggleLiveMarkers}
            aria-label="Toggle live trade markers"
            aria-pressed={showLiveMarkers}
            className={`flex items-center gap-2 rounded-lg border px-3 py-2 transition-all ${
              showLiveMarkers 
                ? 'border-sky-500/30 bg-sky-500/10 text-sky-400' 
                : 'border-white/5 bg-[#25282f]/30 text-gray-500 hover:text-gray-400'
            }`}
          >
            <User size={11} /> Live Markers
          </button>
          
          <div className="h-5 w-px bg-white/5 mx-1" />

          <button 
            onClick={handleClearMarkers}
            title="Clear all markers for this asset"
            className="flex items-center gap-2 rounded-lg border border-white/5 bg-[#25282f] px-3 py-2 text-gray-500 transition-colors hover:border-red-500/30 hover:bg-red-500/10 hover:text-red-400"
          >
            <Eraser size={11} /> Clear
          </button>
        </div>
      </div>

      {series.length === 0 ? (
        <div className="flex min-h-[390px] flex-col items-center justify-center gap-4 px-6 py-12 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#25282f] text-[#ffb800] border border-white/5">
            <Activity size={24} />
          </div>
          <div>
            <p className="text-sm font-black uppercase tracking-widest text-white">Awaiting live telemetry</p>
            <p className="mt-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">
              {warmup ? 'Warmup buffer cycle in execution.' : 'priming WebSocket endpoint for tick data.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="relative min-h-[390px] px-6 pb-6 pt-10">
          <div className="absolute left-6 top-4 z-10 rounded-xl border border-white/5 bg-[#1a1c22]/95 px-4 py-3 shadow-xl backdrop-blur-md">
            <div className="flex items-center gap-3">
              <span className={`h-2.5 w-2.5 rounded-full ${signalDirection === 'call' ? 'bg-emerald-400' : signalDirection === 'put' ? 'bg-[#fe7453]' : 'bg-gray-600'}`} />
              <div>
                <p className="text-[8px] font-black uppercase tracking-widest text-gray-500">Signal</p>
                <p className="text-xs font-bold text-white uppercase">{signalLabel}</p>
              </div>
            </div>
            <div className="mt-2.5 flex items-center gap-2 text-[9px] font-black uppercase tracking-widest border-t border-white/5 pt-2">
              <span className={signalDirection === 'put' ? 'text-[#fe7453]' : 'text-emerald-400'}>
                {signalDirection === 'call' ? 'CALL' : signalDirection === 'put' ? 'PUT' : 'NEUTRAL'}
              </span>
              <span className="text-gray-700">•</span>
              <span className="text-[#ffb800]">{Math.round(signalConfidence)}%</span>
            </div>
          </div>

          <svg className="h-[330px] w-full drop-shadow-[0_0_12px_rgba(255,184,0,0.08)]" viewBox="0 0 1000 360" role="img" aria-label={`${formatAssetLabel(asset)} live sparkline`}>
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
                strokeOpacity="0.04"
                className="text-slate-500"
              />
            ))}

            {path && points.length > 0 && (
              <>
                <path d={`${path} L ${points[points.length - 1].x} 332 L 28 332 Z`} fill="url(#sparklineGlow)" opacity="0.9" />
                <path d={path} fill="none" stroke="url(#sparklineLine)" strokeWidth="4" strokeLinejoin="round" strokeLinecap="round" />
              </>
            )}

            {/* Draw a horizontal tracker line from the latest point to the price label area */}
            {points.length > 0 && (
              <line
                x1={points[points.length - 1].x}
                x2={1000 - 28}
                y1={points[points.length - 1].y}
                y2={points[points.length - 1].y}
                stroke="#ffed6d"
                strokeWidth="1.5"
                strokeDasharray="4 4"
                strokeOpacity="0.4"
              />
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
              const color = isWin ? '#34d399' : isLoss ? '#f87171' : '#ffb800';
              const isGhost = m.kind === 'ghost';
              
              return (
                <g key={m.tradeId}>
                  <line x1="0" x2="1000" y1={y} y2={y} stroke={color} strokeWidth="1.5" strokeDasharray="6 6" strokeOpacity={isWin || isLoss ? "0.4" : "0.8"} />
                  <text x="12" y={y - 8} fill={color} fontSize="11" fontWeight="bold" fontFamily="monospace">
                    {isGhost ? '👻' : '👤'} {(m.direction ?? 'N/A').toUpperCase()}
                  </text>
                  {m.profit != null && (
                    <text x="988" y={y - 8} textAnchor="end" fill={color} fontSize="11" fontWeight="bold" fontFamily="monospace">
                      {m.profit > 0 ? '+' : ''}${Math.abs(m.profit).toFixed(2)}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {latest !== null && lastPriceLabelY !== null && (
            <div
              className="absolute right-6 rounded-lg border border-[#ffb800]/30 bg-[#ffb800]/90 backdrop-blur-sm px-4 py-2.5 text-right shadow-lg transition-[top] duration-300 ease-out z-10"
              style={{ top: lastPriceLabelY, transform: 'translateY(-50%)' }}
            >
              <p className="text-[9px] font-black uppercase tracking-widest text-black/60">Last Price</p>
              <p className="text-lg font-black leading-none text-black font-mono">{formatPrice(latest)}</p>
            </div>
          )}

          <div className="absolute bottom-6 left-6 flex items-center gap-3 text-[9px] font-black uppercase tracking-widest text-gray-400">
            <span className="flex items-center gap-1.5 rounded-lg border border-white/5 bg-[#25282f]/30 px-3 py-1.5 text-white">
              {trendUp ? <ArrowUpRight size={11} className="text-emerald-400" /> : <ArrowDownRight size={11} className="text-rose-400" />}
              {trendUp ? '+' : ''}{trend.toFixed(2)}%
            </span>
            <span className="flex items-center gap-1.5 rounded-lg border border-white/5 bg-[#25282f]/30 px-3 py-1.5 text-white">
              <Layers3 size={11} />
              {series.length} ticks
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
