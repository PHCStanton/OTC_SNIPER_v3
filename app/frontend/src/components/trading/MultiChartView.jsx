/**
 * MultiChartView — compact asset grid for watching multiple OTC charts.
 * Enhanced with modular components: Gauges, Stats, Regime, and Manipulation Pulse.
 */
import React from 'react';
import { Plus, X, Layers3, Star, AlertTriangle } from 'lucide-react';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useStreamStore } from '../../stores/useStreamStore.js';
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

const EMPTY_TICKS = [];

function MultiChartCard({ asset, isSelected, onRemove }) {
  const setSelectedAsset = useAssetStore((s) => s.setSelectedAsset);
  const starredAssets = useAssetStore((s) => s.starredAssets);
  const toggleStar = useAssetStore((s) => s.toggleStarredAsset);
  const isStarred = starredAssets.includes(asset);

  const ticks = useStreamStore((s) => s.ticks?.[asset] ?? EMPTY_TICKS);
  const signal = useStreamStore((s) => s.signals?.[asset] ?? null);
  const context = useStreamStore((s) => s.contexts?.[asset] ?? s.context?.[asset] ?? null);
  const manipulation = useStreamStore((s) => s.manipulation?.[asset] ?? s.manipulations?.[asset] ?? null);
  
  const assetStats = useRiskStore((s) => s.assetStats?.[asset] ?? null);
  const config = useSettingsStore((s) => s.miniChartConfig ?? SETTINGS_DEFAULTS.miniChartConfig);

  const series = extractNumericSeries(ticks);
  const latest = series.length > 0 ? series[series.length - 1] : null;
  const trend = getTrendPercent(series);
  const positive = trend >= 0;

  const direction = getSignalDirection(signal);
  const confidence = getSignalConfidence(signal);
  const regime = context?.regime ?? signal?.regime ?? null;
  const manipulationFlags = manipulation?.flags ?? manipulation;
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

  return (
    <article 
      onDoubleClick={handleDoubleClick}
      className={`group relative rounded-2xl border transition-all duration-300 cursor-pointer overflow-hidden p-3
        ${isSelected 
          ? 'border-[#f5df19]/50 bg-[#282d2e] shadow-[0_0_15px_rgba(245,223,25,0.1)]' 
          : 'border-white/5 bg-[#212127] hover:border-[#f5df19]/40 hover:bg-[#282d2e]'
        }`}
    >
      {/* Manipulation Pulse Overlay */}
      {config.showManipulation && isManipulated && (
        <div className="absolute inset-0 bg-rose-500/5 animate-pulse pointer-events-none" />
      )}

      <div className="flex items-start justify-between gap-3 relative z-10">
        <div className="flex items-center gap-2">
          <button 
            type="button"
            onClick={(e) => { e.stopPropagation(); toggleStar(asset); }}
            className={`transition-colors ${isStarred ? 'text-[#f5df19]' : 'text-gray-600 hover:text-gray-400'}`}
            aria-label={isStarred ? `Unstar ${asset}` : `Star ${asset}`}
          >
            <Star size={14} fill={isStarred ? "currentColor" : "none"} />
          </button>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-gray-500">Asset</p>
            <h4 className="text-sm font-black text-[#e3e6e7]">{formatAssetLabel(asset)}</h4>
          </div>
        </div>

        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onRemove(asset); }}
          className="rounded-full p-1.5 text-gray-500 transition hover:bg-white/5 hover:text-[#e3e6e7]"
          aria-label={`Remove ${asset}`}
        >
          <X size={12} />
        </button>
      </div>

      <div className="mt-2 flex items-center justify-between gap-3 relative z-10">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">Price</p>
          <p className="text-base font-black text-[#e3e6e7]">{formatPrice(latest)}</p>
        </div>

        <div className="flex flex-col items-end gap-1">
          <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${positive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-[#fe7453]/10 text-[#fe7453]'}`}>
            {positive ? '+' : ''}{trend.toFixed(2)}%
          </span>
          {config.showRegime && regime && (
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-white/5 text-gray-400 border border-white/5 uppercase tracking-tighter">
              {String(regime).replaceAll('_', ' ')}
            </span>
          )}
        </div>
      </div>

      <div className={`mt-3 relative h-16 transition-opacity duration-300 ${config.showGauge && confidence > 0 ? 'group-hover:opacity-20' : ''}`}>
        {config.showSparkline && <MiniSparkline ticks={ticks} />}
      </div>

      {/* Hybrid Gauge Overlay */}
      {config.showGauge && confidence > 0 && (
        <div className="absolute inset-x-0 top-12 flex flex-col items-center justify-center pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <div className="relative w-16 h-16">
             <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="3" className="text-white/5" />
                <circle 
                  cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="3" 
                  strokeDasharray={`${confidence} 100`}
                  className={direction === 'call' ? 'text-emerald-500' : 'text-[#fe7453]'}
                  strokeLinecap="round"
                />
             </svg>
             <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-[10px] font-black text-[#e3e6e7]">{Math.round(confidence)}%</span>
             </div>
          </div>
          <span className={`text-[9px] font-black uppercase tracking-[0.2em] mt-1 ${direction === 'call' ? 'text-emerald-500' : 'text-[#fe7453]'}`}>
            {direction || 'NEUTRAL'}
          </span>
        </div>
      )}

      <div className="mt-3 flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500 relative z-10">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <Layers3 size={11} />
            {series.length}
          </span>
          {config.showStats && assetStats && (
            <span className="flex items-center gap-1 font-bold">
              <span className="text-emerald-500">{assetStats.w}W</span>
              <span className="opacity-30">/</span>
              <span className="text-rose-500">{assetStats.l}L</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {config.showManipulation && isManipulated && (
            <AlertTriangle size={12} className="text-rose-500 animate-pulse" />
          )}
          <span className={isSelected ? 'text-[#f5df19] font-bold' : ''}>
            {isSelected ? 'SELECTED' : 'WATCHING'}
          </span>
        </div>
      </div>
    </article>
  );
}

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
