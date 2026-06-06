/**
 * MultiChartView — compact asset grid for watching multiple OTC charts.
 * Enhanced with modular components: Gauges, Stats, Regime, and Manipulation Pulse.
 * Redesigned to follow the Stitch Design Reference.
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

  const config = useSettingsStore((s) => s.miniChartConfig ?? SETTINGS_DEFAULTS.miniChartConfig);
  
  // Phase 2: Split store subscriptions
  const latestPrice = useStreamStore((s) => s.latestPrice?.[asset] ?? null);
  const ticks = useStreamStore((s) => config.showSparkline ? (s.ticks?.[asset] ?? EMPTY_TICKS) : EMPTY_TICKS);
  const signal = useStreamStore((s) => s.signals?.[asset] ?? null);
  const manipulation = useStreamStore((s) => s.manipulation?.[asset] ?? null);
  const isWarmup = useStreamStore((s) => Boolean(s.warmup?.[asset]));
  
  const assetStats = useRiskStore((s) => s.assetStats?.[asset] ?? null);
  const [isHovered, setIsHovered] = React.useState(false);

  const series = React.useMemo(() => extractNumericSeries(ticks), [ticks]);
  const { latest, trend, positive, direction, confidence } = React.useMemo(() => {
    const t = getTrendPercent(series);
    return {
      latest: latestPrice ?? (series.length > 0 ? series[series.length - 1] : null),
      trend: t,
      positive: t >= 0,
      direction: getSignalDirection(signal),
      confidence: getSignalConfidence(signal),
    };
  }, [series, signal, latestPrice]);
  
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

  const shouldRenderGauge = config.showGauge && confidence > 0 && (!config.gaugeOnHover || isHovered);

  return (
    <article 
      onDoubleClick={handleDoubleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`group relative rounded-xl border transition-all duration-300 cursor-pointer overflow-hidden p-4 min-h-[160px] flex flex-col justify-between
        ${isSelected 
          ? 'border-[#ffb800]/40 bg-[#25282f]/50 shadow-[0_0_15px_rgba(255,184,0,0.06)]' 
          : 'border-white/5 bg-[#25282f]/20 hover:border-[#ffb800]/25 hover:bg-[#25282f]/30'
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
        <div className="flex items-center gap-2.5">
          <button 
            type="button"
            onClick={(e) => { e.stopPropagation(); toggleStar(asset); }}
            className={`transition-colors ${isStarred ? 'text-[#ffb800]' : 'text-gray-600 hover:text-gray-400'}`}
            aria-label={isStarred ? `Unstar ${asset}` : `Star ${asset}`}
          >
            <Star size={12} className={isStarred ? "fill-current" : ""} />
          </button>
          <h4 className={`text-xs font-black uppercase tracking-wider transition-colors ${isSelected ? 'text-[#ffb800]' : 'text-white'}`}>
            {formatAssetLabel(asset)}
          </h4>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end">
            <span className="text-[8px] font-black uppercase tracking-widest text-gray-500 leading-none mb-1">Payout</span>
            <span className="text-[10px] font-black text-emerald-400 leading-none">{Math.round(payout * 100)}%</span>
          </div>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onRemove(asset); }}
            className="rounded p-1 text-gray-600 transition hover:bg-white/5 hover:text-white"
            aria-label={`Remove ${asset}`}
          >
            <X size={12} />
          </button>
        </div>
      </div>

      {/* CENTER AREA (GAUGE) */}
      <div className="relative flex-1 flex items-center justify-center py-2 z-10 min-h-[76px] transition-all duration-300">
        {shouldRenderGauge && (
          <div className="relative flex items-center justify-center w-full max-w-[200px]">
            {/* BUY Text */}
            <div className={`absolute left-0 text-[10px] font-black uppercase tracking-widest transition-colors ${direction === 'call' ? 'text-emerald-500' : 'text-gray-600/50'}`}>
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
                  <span className="text-xs font-black text-white">{Math.round(confidence)}%</span>
               </div>
               
               {/* NTRL below */}
               <div className="absolute -bottom-3 left-0 right-0 flex justify-center">
                 <span className={`text-[8px] font-black uppercase tracking-widest transition-colors ${!direction ? 'text-blue-400' : 'text-gray-600/50'}`}>
                   NTRL
                 </span>
               </div>
            </div>

            {/* SELL Text */}
            <div className={`absolute right-0 text-[10px] font-black uppercase tracking-widest transition-colors ${direction === 'put' ? 'text-[#fe7453]' : 'text-gray-600/50'}`}>
              SELL
            </div>
          </div>
        )}
      </div>

      {/* BOTTOM ROW */}
      <div className="flex items-end justify-between relative z-10 mt-2 border-t border-white/5 pt-2">
        {/* Bottom Left: Price & Trend */}
        <div className="flex flex-col items-start gap-1 w-1/3">
          <div>
            <p className="text-[8px] font-black uppercase tracking-widest text-gray-500 leading-none mb-1">Price</p>
            <p className="text-[11px] font-bold text-white font-mono leading-none">{formatPrice(latest)}</p>
          </div>
          <span className={`rounded px-1.5 py-0.5 text-[8px] font-black tracking-widest ${positive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-[#fe7453]/10 text-[#fe7453]'}`}>
            {positive ? '+' : ''}{trend.toFixed(2)}%
          </span>
        </div>

        {/* Bottom Center: W/L Stats + Manipulation */}
        <div className="flex flex-col items-center justify-end w-1/3 pb-1 gap-1">
          <div className="flex items-center gap-1.5">
            <span className="text-[8px] font-black uppercase tracking-widest text-gray-500 leading-none">W</span>
            <span className="text-[11px] font-bold text-emerald-400 leading-none">
              {assetStats?.w ?? 0}
            </span>
            <span className="text-[10px] text-gray-600 leading-none">/</span>
            <span className="text-[11px] font-bold text-[#fe7453] leading-none">
              {assetStats?.l ?? 0}
            </span>
            <span className="text-[8px] font-black uppercase tracking-widest text-gray-500 leading-none">L</span>
          </div>
          {config.showManipulation && isManipulated && (
            <AlertTriangle size={12} className="text-rose-500 animate-pulse" />
          )}
        </div>

        {/* Bottom Right: Regime & Ticker */}
        <div className="flex flex-col items-end gap-2.5 w-1/3">
          {config.showRegime && (
            <div className="text-right">
              <p className="text-[8px] font-black uppercase tracking-widest text-gray-500 leading-none mb-1">Regime</p>
              <p className="text-[9px] font-black text-gray-300 uppercase tracking-tighter leading-none truncate max-w-[80px]">
                {regime ? String(regime).replaceAll('_', ' ') : 'UNAVAIL'}
              </p>
            </div>
          )}
          <div className="flex items-center gap-1.5 text-[9px] font-black text-gray-500 uppercase tracking-wider">
            {isWarmup ? (
              <span className="text-[#ffb800] uppercase tracking-widest text-[8px] font-black mr-1 animate-pulse">Warmup</span>
            ) : null}
            <Layers3 size={10} />
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
    <section className="flex h-full flex-col rounded-[20px] bg-[#1a1c22] p-6 shadow-xl border border-white/5">
      <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-4 shrink-0">
        <div>
          <p className="text-[10px] font-black uppercase tracking-widest text-[#ffb800]">Asset Watchlist</p>
          <h3 className="mt-1 text-md font-black uppercase tracking-wider text-white">Multi-Chart Panel</h3>
        </div>

        <button
          type="button"
          disabled={!canAddSelected}
          onClick={() => addMultiChartAsset(selectedAsset)}
          className="flex items-center gap-2 rounded-lg border border-white/5 bg-[#25282f] px-4 py-2 text-[10px] font-black uppercase tracking-widest text-gray-400 transition hover:bg-[#2d3139] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Plus size={12} />
          Add Selected
        </button>
      </div>

      <div className="mt-4 grid gap-4 overflow-y-auto sm:grid-cols-2 xl:grid-cols-3 flex-1 custom-scrollbar">
        {multiChartAssets.map((asset) => (
          <MultiChartCard
            key={asset}
            asset={asset}
            isSelected={asset === selectedAsset}
            onRemove={removeMultiChartAsset}
          />
        ))}
        {multiChartAssets.length === 0 && (
          <div className="col-span-full flex flex-col items-center justify-center py-12 text-center opacity-30">
            <Layers3 size={32} className="mb-3 text-gray-500" />
            <p className="text-[10px] font-black uppercase tracking-widest text-white">Watchlist Empty</p>
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mt-1">Add assets above to monitor live charts.</p>
          </div>
        )}
      </div>
    </section>
  );
}
