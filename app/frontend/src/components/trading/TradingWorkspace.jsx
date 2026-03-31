/**
 * TradingWorkspace — Phase 5 trading-terminal surface.
 * This assembles the chart, signal ring, execution panel, history, and multi-chart widgets.
 */
import { Activity, ShieldCheck, Wallet, Zap } from 'lucide-react';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { useStreamStore } from '../../stores/useStreamStore.js';
import { useTradingStore } from '../../stores/useTradingStore.js';
import { formatAssetLabel, formatPrice, getTrendPercent, extractNumericSeries, getSignalLabel } from './chartUtils.js';
import Sparkline from './Sparkline.jsx';
import OTEORing from './OTEORing.jsx';
import TradePanel from './TradePanel.jsx';
import TradeHistory from './TradeHistory.jsx';
import MultiChartView from './MultiChartView.jsx';

function MetricCard({ label, value, note, icon: Icon, tone = 'neutral', children }) {
  const toneClasses = {
    neutral: 'border-white/5 bg-[#212127] text-[#e3e6e7]',
    sky: 'border-white/5 bg-[#212127] text-[#e3e6e7]',
    emerald: 'border-emerald-500/20 bg-[#212127] text-[#e3e6e7]',
    amber: 'border-white/5 bg-[#212127] text-[#e3e6e7]',
  };

  return (
    <section className={`rounded-lg border p-4 shadow-[0_10px_24px_rgba(0,0,0,0.22)] backdrop-blur ${toneClasses[tone] || toneClasses.neutral}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-500">{label}</p>
          <p className="mt-1 text-xl font-black tracking-tight text-[#e3e6e7]">{value}</p>
          {note && <p className="mt-1 text-[11px] font-medium text-gray-500">{note}</p>}
        </div>

        {Icon && (
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#1a1717] text-[#f5df19] shadow-sm">
            <Icon size={16} />
          </div>
        )}
      </div>
      {children && <div className="mt-3">{children}</div>}
    </section>
  );
}

export default function TradingWorkspace() {
  const { selectedAsset } = useAssetStore();
  const { chromeStatus, sessionStatus, balance, accountType, error: opsError } = useOpsStore();
  const { ticks, signals, warmup } = useStreamStore();
  const { lastTradeResult, tradeError } = useTradingStore();

  const selectedTicks = ticks[selectedAsset] || [];
  const selectedSignal = signals[selectedAsset] || null;
  const selectedSeries = extractNumericSeries(selectedTicks);
  const latestPrice = selectedSeries.length > 0 ? selectedSeries[selectedSeries.length - 1] : null;
  const trend = getTrendPercent(selectedSeries);
  const signalLabel = getSignalLabel(selectedSignal);

  const sessionConnected = sessionStatus === 'connected';
  const chromeRunning = chromeStatus === 'running';

  const resultLabel = lastTradeResult
    ? (lastTradeResult.outcome ? lastTradeResult.outcome.toUpperCase() : lastTradeResult.message ? 'SUBMITTED' : 'RECORDED')
    : 'AWAITING TRADE';

  const resultTone = lastTradeResult && typeof lastTradeResult.pnl === 'number'
    ? lastTradeResult.pnl >= 0
      ? 'emerald'
      : 'amber'
    : 'neutral';

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top,_rgba(255,237,109,0.10),_transparent_35%),linear-gradient(180deg,#0c0f0f_0%,#111414_54%,#171a1b_100%)] px-4 py-4 text-[#e3e6e7] lg:px-6 lg:py-6">
      <div className="mx-auto flex max-w-[1700px] flex-col gap-4">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Signal confidence"
            value={warmup[selectedAsset] ? 'WARMUP' : signalLabel}
            note={warmup[selectedAsset] ? 'Waiting for the asset to finish warmup.' : `Live signal for ${formatAssetLabel(selectedAsset)}`}
            icon={Activity}
            tone={warmup[selectedAsset] ? 'neutral' : 'sky'}
          >
            <OTEORing asset={selectedAsset} signal={selectedSignal} warmup={Boolean(warmup[selectedAsset])} />
          </MetricCard>

          <MetricCard
            label="Selected asset"
            value={formatAssetLabel(selectedAsset)}
            note={latestPrice !== null ? `Last tick ${formatPrice(latestPrice)} · Trend ${trend >= 0 ? '+' : ''}${trend.toFixed(2)}%` : 'No live ticks yet'}
            icon={Zap}
            tone="amber"
          />

          <MetricCard
            label="Session gate"
            value={sessionConnected ? 'CONNECTED' : 'DISCONNECTED'}
            note={chromeRunning ? 'Chrome is running and ready for SSID work.' : 'Chrome is stopped.'}
            icon={ShieldCheck}
            tone={sessionConnected ? 'emerald' : 'neutral'}
          >
            <div className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-[0.18em] opacity-70">
              <span>Account</span>
              <span>{accountType ? accountType.toUpperCase() : '—'}</span>
            </div>
            <div className="mt-2 flex items-center justify-between text-[11px] font-semibold uppercase tracking-[0.18em] opacity-70">
              <span>Balance</span>
              <span>${Number(balance || 0).toFixed(2)}</span>
            </div>
          </MetricCard>

          <MetricCard
            label="Latest result"
            value={resultLabel}
            note={lastTradeResult && typeof lastTradeResult.pnl === 'number'
              ? `PnL ${lastTradeResult.pnl > 0 ? '+' : ''}${lastTradeResult.pnl.toFixed(2)}`
              : lastTradeResult?.message || tradeError || opsError || 'Trade output will appear here.'}
            icon={Wallet}
            tone={resultTone}
          />
        </section>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_380px]">
          <Sparkline
            asset={selectedAsset}
            ticks={selectedTicks}
            signal={selectedSignal}
            warmup={Boolean(warmup[selectedAsset])}
          />
          <TradePanel />
        </section>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <TradeHistory />
          <MultiChartView />
        </section>
      </div>
    </div>
  );
}
