/**
 * MultiChartView — compact asset grid for watching multiple OTC charts.
 * Enhanced with modular components: Gauges, Stats, Regime, and Manipulation Pulse.
 */
import React from 'react';
import { Plus, X, Layers3, Star, AlertTriangle } from 'lucide-react';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useStreamStore, EMPTY_TICKS } from '../../stores/useStreamStore.js';
import { SETTINGS_DEFAULTS, useSettingsStore } from '../../stores/useSettingsStore.js';
import { useRiskStore } from '../../stores/useRiskStore.js';
import { 
  formatAssetLabel, 
  formatPrice, 
  getTrendPercent, 
  extractNumericSeries,
  getSignalDirection,
  getSignalConfidence
} from './chartUtils.js';
import MiniSparkline from './MiniSparkline.jsx';

function getMiniGaugeTone(direction) {
  if (direction === 'call') {
    return {
      stroke: 'text-emerald-500',
      label: 'text-emerald-500',
    };
  }

  if (direction === 'put') {
    return {
      stroke: 'text-[#fe7453]',
      label: 'text-[#fe7453]',
    };
  }

  return {
    stroke: 'text-blue-400',
    label: 'text-blue-400',
  };
}

const MultiChartCard = React.memo(function MultiChartCard({ asset, isSelected, onRemove }) {
  const setSelectedAsset = useAssetStore((s) => s.setSelectedAsset);
  const starredAssets = useAssetStore((s) => s.starredAssets);
  const toggleStar = useAssetStore((s) => s.toggleStarredAsset);
  const isStarred = starredAssets.includes(asset);
  const payout = useAssetStore((s) => s.assetPayouts[asset] ?? s.assetDetails[asset]?.payout ?? 0);

  const ticks = useStreamStore((s) => s.ticks?.[asset] ?? EMPTY_TICKS);
  const signal = useStreamStore((s) => s.signals?.[asset] ?? null);
  const manipulation = useStreamStore((s) => s.manipulation?.[asset] ?? null);
  const isWarmup = useStreamStore((s) => Boolean(s.warmup?.[asset]));
  
  const assetStats = useRiskStore((s) => s.assetStats?.[asset] ?? null);
  const config = useSettingsStore((s) => s.miniChartConfig ?? SETTINGS_DEFAULTS.miniChartConfig);

  const series = React.useMemo(() => extractNumericSeries(ticks), [ticks]);
  const { latest, trend, positive, direction, confidence } = React.useMemo(() => {
    const t = getTrendPercent(series);
    return {
      latest: series.length > 0 ? series[series.length - 1] : null,
      trend: t,
      positive: t >= 0,
      direction: getSignalDirection(signal),
      confidence: getSignalConfidence(signal),
    };
  }, [series, signal]);
  
  const regime = signal?.regime ?? null;
  const manipulationFlags = manipulation?.flags ?? manipulation;
  const gaugeTone = getMiniGaugeTone(direction);
  const isManipulated = Boolean(
    manipulation?.detected
    || manipulation?.type
    || manipulationFlags?.is_push_snap
    || manipulationFlags?.is_velocity_spike
    || manipulationFlags?.push_and_snap
  );

  const handleDoubleClick = () => {
    setSelectedAsset(asset);
  };

  const gaugeVisibilityClass = config.gaugeOnHover 
    ? 'opacity-0 group-hover:opacity-100' 
    : 'opacity-100';

  return (
    <article 
      onDoubleClick={handleDoubleClick}
      className={`group relative rounded-2xl border transition-all duration-300 cursor-pointer overflow-hidden p-3 min-h-[160px] flex flex-col justify-between
        ${isSelected 
          ? 'border-[#f5df19]/50 bg-[#282d2e] shadow-[0_0_15px_rgba(245,223,25,0.1)]' 
          : 'border-white/5 bg-[#212127] hover:border-[#f5df19]/40 hover:bg-[#282d2e]'
        }`}
    >
      {/* Manipulation Pulse Overlay */}
      {config.showManipulation && isManipulated && (
        <div className="absolute inset-0 bg-rose-500/5 animate-pulse pointer-events-none z-0" />
      )}

      {/* Sparkline Background */}
      {config.showSparkline && (
        <div className="absolute inset-x-0 bottom-12 top-10 opacity-20 z-0 pointer-events-none">
          <MiniSparkline ticks={ticks} className="h-full w-full !border-none !bg-transparent" />
        </div>
      )}

      {/* TOP ROW */}
      <div className="flex items-start justify-between gap-2 relative z-10">
        <div className="flex items-center gap-2">
          <button 
            type="button"
            onClick={(e) => { e.stopPropagation(); toggleStar(asset); }}
            className={`transition-colors ${isStarred ? 'text-[#f5df19]' : 'text-gray-600 hover:text-gray-400'}`}
            aria-label={isStarred ? `Unstar ${asset}` : `Star ${asset}`}
          >
            <Star size={14} fill={isStarred ? "currentColor" : "none"} />
          </button>
          <h4 className={`text-sm font-black uppercase tracking-wider transition-colors ${isSelected ? 'text-[#f5df19]' : 'text-[#e3e6e7]'}`}>
            {formatAssetLabel(asset)}
          </h4>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end">
            <span className="text-[9px] font-semibold uppercase tracking-[0.2em] text-gray-500 leading-none mb-1">Payout</span>
            <span className="text-xs font-bold text-emerald-400 leading-none">{Math.round(payout * 100)}%</span>
          </div>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onRemove(asset); }}
            className="rounded-full p-1 text-gray-500 transition hover:bg-white/5 hover:text-[#e3e6e7]"
            aria-label={`Remove ${asset}`}
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* CENTER AREA (GAUGE) */}
      <div className={`relative flex-1 flex items-center justify-center py-2 z-10 transition-opacity duration-300 ${gaugeVisibilityClass}`}>
        {config.showGauge && confidence > 0 && (
          <div className="relative flex items-center justify-center w-full max-w-[200px]">
            {/* BUY Text */}
            <div className={`absolute left-0 text-[10px] sm:text-xs font-black uppercase tracking-widest transition-colors ${direction === 'call' ? 'text-emerald-500' : 'text-gray-600/50'}`}>
              BUY
            </div>

            {/* Gauge */}
            <div className="relative h-[72px] w-[72px]">
               <svg className="h-full w-full -rotate-90" viewBox="0 0 36 36">
                  <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="3" className="text-white/5" />
                  <circle 
                    cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="3" 
                    strokeDasharray={`${confidence} 100`}
                    className={gaugeTone.stroke}
                    strokeLinecap="round"
                  />
               </svg>
               <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-sm font-black text-[#e3e6e7]">{Math.round(confidence)}%</span>
               </div>
               
               {/* NTRL below */}
               <div className="absolute -bottom-3 left-0 right-0 flex justify-center">
                 <span className={`text-[9px] font-black uppercase tracking-widest transition-colors ${!direction ? 'text-blue-400' : 'text-gray-600/50'}`}>
                   NTRL
                 </span>
               </div>
            </div>

            {/* SELL Text */}
            <div className={`absolute right-0 text-[10px] sm:text-xs font-black uppercase tracking-widest transition-colors ${direction === 'put' ? 'text-[#fe7453]' : 'text-gray-600/50'}`}>
              SELL
            </div>
          </div>
        )}
      </div>

      {/* BOTTOM ROW */}
      <div className="flex items-end justify-between relative z-10 mt-2">
        {/* Bottom Left: Price & Trend */}
        <div className="flex flex-col items-start gap-1.5 w-1/3">
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-gray-500 leading-none mb-1">Price</p>
            <p className="text-[13px] font-black text-[#e3e6e7] leading-none">{formatPrice(latest)}</p>
          </div>
          <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold tracking-wider ${positive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-[#fe7453]/10 text-[#fe7453]'}`}>
            {positive ? '+' : ''}{trend.toFixed(2)}%
          </span>
        </div>

        {/* Bottom Center: W/L Stats + Manipulation */}
        <div className="flex flex-col items-center justify-end w-1/3 pb-1 gap-1">
          <div className="flex items-center gap-1.5">
            <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-gray-500 leading-none">W</span>
            <span className="text-[13px] font-black text-emerald-400 leading-none">
              {assetStats?.w ?? 0}
            </span>
            <span className="text-[10px] text-gray-600 leading-none">/</span>
            <span className="text-[13px] font-black text-[#fe7453] leading-none">
              {assetStats?.l ?? 0}
            </span>
            <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-gray-500 leading-none">L</span>
          </div>
          {config.showManipulation && isManipulated && (
            <AlertTriangle size={14} className="text-rose-500 animate-pulse" />
          )}
        </div>

        {/* Bottom Right: Regime & Ticker */}
        <div className="flex flex-col items-end gap-2 w-1/3">
          {config.showRegime && (
            <div className="text-right">
              <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-gray-500 leading-none mb-1">Regime</p>
              <p className="text-[10px] font-bold text-gray-300 uppercase tracking-tighter leading-none">
                {regime ? String(regime).replaceAll('_', ' ') : 'UNAVAIL'}
              </p>
            </div>
          )}
          <div className="flex items-center gap-1.5 text-[10px] font-semibold text-gray-400">
            {isWarmup ? (
              <span className="text-[#ffb800] uppercase tracking-wider text-[9px] font-bold mr-1">Warmup</span>
            ) : null}
            <Layers3 size={11} />
            <span>{series.length}</span>
          </div>
        </div>
      </div>
    </article>
  );
});

export default function MultiChartView() {
  const selectedAsset = useAssetStore((state) => state.selectedAsset);
  const multiChartAssets = useAssetStore((state) => state.multiChartAssets);
  const addMultiChartAsset = useAssetStore((state) => state.addMultiChartAsset);
  const removeMultiChartAsset = useAssetStore((state) => state.removeMultiChartAsset);

  const canAddSelected = !multiChartAssets.includes(selectedAsset) && multiChartAssets.length < 9;

  return (
    <section className="flex h-full flex-col rounded-xl border border-white/5 bg-[#1a1717] p-4 shadow-2xl shadow-black/30 backdrop-blur">
      <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-3 shrink-0">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-500">Watchlist</p>
          <h3 className="text-lg font-black tracking-tight text-[#e3e6e7]">Multi-chart view</h3>
        </div>

        <button
          type="button"
          disabled={!canAddSelected}
          onClick={() => addMultiChartAsset(selectedAsset)}
          className="flex items-center gap-2 rounded-full border border-white/5 bg-[#212127] px-3 py-1.5 text-xs font-semibold text-[#e3e6e7] transition hover:bg-[#282d2e] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Plus size={12} />
          Add selected
        </button>
      </div>

      <div className="mt-4 grid gap-3 overflow-y-auto sm:grid-cols-2 xl:grid-cols-3 flex-1 custom-scrollbar">
        {multiChartAssets.map((asset) => (
          <MultiChartCard
            key={asset}
            asset={asset}
            isSelected={asset === selectedAsset}
            onRemove={removeMultiChartAsset}
          />
        ))}
        {multiChartAssets.length === 0 && (
          <div className="col-span-full flex flex-col items-center justify-center py-12 text-center opacity-20">
            <Layers3 size={48} className="mb-4" />
            <p className="text-sm font-bold uppercase tracking-widest">No assets in watchlist</p>
            <p className="text-xs mt-1">Add assets to monitor multiple charts at once.</p>
          </div>
        )}
      </div>
    </section>
  );
}
