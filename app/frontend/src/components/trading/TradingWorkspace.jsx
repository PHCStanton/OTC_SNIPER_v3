/**
 * TradingWorkspace — Phase 5 trading-terminal surface.
 * This assembles the chart, signal ring, execution panel, history, and multi-chart widgets.
 */
import { Activity } from 'lucide-react';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useStreamStore } from '../../stores/useStreamStore.js';
import Sparkline from './Sparkline.jsx';
import OTEORing from './OTEORing.jsx';
import TradePanel from './TradePanel.jsx';
import TradeHistory from './TradeHistory.jsx';
import MultiChartView from './MultiChartView.jsx';

const EMPTY_TICKS = [];

function MetricCard({ label, value, note, icon: Icon, tone = 'neutral', children }) {
  const toneClasses = {
    neutral: 'border-white/5 bg-[#212127] text-[#e3e6e7]',
    sky: 'border-white/5 bg-[#212127] text-[#e3e6e7]',
    emerald: 'border-emerald-500/20 bg-[#212127] text-[#e3e6e7]',
    amber: 'border-white/5 bg-[#212127] text-[#e3e6e7]',
  };

  return (
    <section className={`flex h-full flex-col rounded-lg border p-4 shadow-[0_10px_24px_rgba(0,0,0,0.22)] backdrop-blur ${toneClasses[tone] || toneClasses.neutral}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-500">{label}</p>
          {value && <p className="mt-1 text-xl font-black tracking-tight text-[#e3e6e7]">{value}</p>}
          {note && <p className="mt-1 text-[11px] font-medium text-gray-500">{note}</p>}
        </div>

        {Icon && (
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#1a1717] text-[#f5df19] shadow-sm">
            <Icon size={16} />
          </div>
        )}
      </div>
      {children && <div className="mt-3 flex-1 flex items-center justify-center">{children}</div>}
    </section>
  );
}

export default function TradingWorkspace() {
  const selectedAsset = useAssetStore((s) => s.selectedAsset);
  
  // Selective subscriptions to avoid re-rendering the whole workspace on every tick of any asset
  const selectedTicks = useStreamStore((s) => s.ticks[selectedAsset] ?? EMPTY_TICKS);
  const selectedSignal = useStreamStore((s) => s.signals[selectedAsset] ?? null);
  const isWarmup = useStreamStore((s) => Boolean(s.warmup[selectedAsset]));

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top,_rgba(255,237,109,0.10),_transparent_35%),linear-gradient(180deg,#0c0f0f_0%,#111414_54%,#171a1b_100%)] px-4 py-4 text-[#e3e6e7] lg:px-6 lg:py-6">
      <div className="mx-auto flex max-w-[1700px] flex-col gap-4">
        <section className="grid gap-4 xl:grid-cols-[380px_minmax(0,1fr)]">
          <TradePanel />
          <MultiChartView />
        </section>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_380px]">
          <Sparkline
            asset={selectedAsset}
            ticks={selectedTicks}
            signal={selectedSignal}
            warmup={isWarmup}
          />
          <MetricCard
            label="Signal confidence"
            icon={Activity}
            tone={isWarmup ? 'neutral' : 'sky'}
          >
            <OTEORing asset={selectedAsset} signal={selectedSignal} warmup={isWarmup} />
          </MetricCard>
        </section>

        <section>
          <TradeHistory />
        </section>
      </div>
    </div>
  );
}
