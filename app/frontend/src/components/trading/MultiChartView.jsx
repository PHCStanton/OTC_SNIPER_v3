/**
 * MultiChartView — compact asset grid for watching multiple OTC charts.
 */
import { Plus, X, Layers3 } from 'lucide-react';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useStreamStore } from '../../stores/useStreamStore.js';
import { formatAssetLabel, formatPrice, getTrendPercent, extractNumericSeries } from './chartUtils.js';
import MiniSparkline from './MiniSparkline.jsx';

export default function MultiChartView() {
  const { selectedAsset, multiChartAssets, addMultiChartAsset, removeMultiChartAsset } = useAssetStore();
  const { ticks } = useStreamStore();

  const canAddSelected = !multiChartAssets.includes(selectedAsset) && multiChartAssets.length < 9;

  return (
    <section className="rounded-xl border border-white/5 bg-[#1a1717] p-4 shadow-2xl shadow-black/30 backdrop-blur">
      <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-3">
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

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {multiChartAssets.map((asset) => {
          const series = extractNumericSeries(ticks[asset]);
          const latest = series.length > 0 ? series[series.length - 1] : null;
          const trend = getTrendPercent(series);
          const positive = trend >= 0;

          return (
            <article key={asset} className="group rounded-2xl border border-white/5 bg-[#212127] p-3 transition hover:border-[#f5df19]/40 hover:bg-[#282d2e]">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-gray-500">Asset</p>
                  <h4 className="text-sm font-black text-[#e3e6e7]">{formatAssetLabel(asset)}</h4>
                </div>

                <button
                  type="button"
                  onClick={() => removeMultiChartAsset(asset)}
                  className="rounded-full p-1.5 text-gray-500 transition hover:bg-white/5 hover:text-[#e3e6e7]"
                  aria-label={`Remove ${asset}`}
                >
                  <X size={12} />
                </button>
              </div>

              <div className="mt-2 flex items-center justify-between gap-3">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">Price</p>
                  <p className="text-base font-black text-[#e3e6e7]">{formatPrice(latest)}</p>
                </div>

                <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${positive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-[#fe7453]/10 text-[#fe7453]'}`}>
                  {positive ? '+' : ''}{trend.toFixed(2)}%
                </span>
              </div>

              <div className="mt-3">
                <MiniSparkline ticks={ticks[asset]} />
              </div>

              <div className="mt-3 flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">
                <span className="flex items-center gap-1.5">
                  <Layers3 size={11} />
                  {series.length} ticks
                </span>
                <span>{asset === selectedAsset ? 'Selected' : 'Watching'}</span>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
