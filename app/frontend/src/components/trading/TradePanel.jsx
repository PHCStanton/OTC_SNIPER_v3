/**
 * TradePanel — execution controls for the Phase 5 trading workspace.
 */
import { useMemo } from 'react';
import { ArrowDownRight, ArrowUpRight, AlertTriangle, DollarSign, Ghost, Loader2, Wallet } from 'lucide-react';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { useTradingStore } from '../../stores/useTradingStore.js';
import { formatAssetLabel } from './chartUtils.js';

export default function TradePanel() {
  const { selectedAsset } = useAssetStore();
  const { sessionStatus, balance, accountType } = useOpsStore();
  const {
    amount,
    duration,
    isGhost,
    isExecuting,
    tradeError,
    lastTradeResult,
    setAmount,
    setDuration,
    setIsGhost,
    setDirection,
    executeTrade,
  } = useTradingStore();

  const sessionConnected = sessionStatus === 'connected';
  const broker = 'pocket_option';

  const parsedAmount = useMemo(() => {
    const value = Number(amount);
    return Number.isFinite(value) ? value : 0;
  }, [amount]);

  const parsedDuration = useMemo(() => {
    const value = Number(duration);
    return Number.isFinite(value) ? value : 0;
  }, [duration]);

  const canTrade = sessionConnected && !isExecuting && parsedAmount > 0 && parsedDuration > 0;

  async function handleExecute(direction) {
    if (!sessionConnected || isExecuting || parsedAmount <= 0 || parsedDuration <= 0) return;
    setDirection(direction);
    await executeTrade(broker, selectedAsset);
  }

  return (
    <section className="flex h-full flex-col rounded-xl border border-white/5 bg-[#1a1717] p-4 shadow-2xl shadow-black/30 backdrop-blur">
      <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-500">Execution panel</p>
          <h3 className="text-lg font-black tracking-tight text-[#e3e6e7]">{formatAssetLabel(selectedAsset)}</h3>
        </div>
        <div className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${sessionConnected ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400' : 'border-white/5 bg-[#212127] text-gray-500'}`}>
          {sessionConnected ? <DollarSign size={11} /> : <Ghost size={11} />}
          {accountType ? accountType.toUpperCase() : 'NO SESSION'}
        </div>
      </div>

      <div className="mt-4 space-y-4">
        <div>
          <label className="mb-1 block text-[10px] font-bold uppercase tracking-[0.22em] text-gray-500">Trade amount</label>
          <div className="relative">
            <input
              type="number"
              min="1"
              step="0.1"
              value={amount}
              onChange={(event) => setAmount(Number(event.target.value))}
              className="w-full rounded-xl border border-white/10 bg-white px-4 py-3 pr-20 text-lg font-black text-black outline-none transition focus:border-[#f5df19] focus:bg-white"
            />
            <div className="absolute inset-y-0 right-3 flex items-center text-gray-500">
              <Wallet size={16} />
            </div>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-[10px] font-bold uppercase tracking-[0.22em] text-gray-500">Expiration</label>
          <input
            type="number"
            min="10"
            step="5"
            value={duration}
            onChange={(event) => setDuration(Number(event.target.value))}
            className="w-full rounded-xl border border-white/10 bg-white px-4 py-3 text-base font-bold text-black outline-none transition focus:border-[#f5df19] focus:bg-white"
          />
          <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">Seconds</p>
        </div>

        <label className="flex items-center justify-between rounded-xl border border-white/5 bg-[#212127] px-4 py-3">
          <div>
            <p className="text-xs font-bold text-[#e3e6e7]">Ghost trading</p>
            <p className="text-[10px] text-gray-500">Simulate the trade without using the live account</p>
          </div>
          <button
            type="button"
            onClick={() => setIsGhost(!isGhost)}
            className={`flex h-7 w-12 items-center rounded-full p-1 transition ${isGhost ? 'bg-[#f5df19]' : 'bg-[#444949]'}`}
            aria-pressed={isGhost}
            aria-label="Toggle ghost trading"
          >
            <span className={`h-5 w-5 rounded-full bg-white transition ${isGhost ? 'translate-x-5' : 'translate-x-0'}`} />
          </button>
        </label>

        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            disabled={!canTrade}
            onClick={() => void handleExecute('call')}
            className="flex flex-col items-center justify-center rounded-lg bg-[#22c55e] px-4 py-5 text-white shadow-lg shadow-emerald-500/20 transition hover:bg-[#34d399] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isExecuting ? <Loader2 className="mb-1 animate-spin" size={24} /> : <ArrowUpRight size={26} className="mb-1" />}
            <span className="text-sm font-black tracking-wide">CALL</span>
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] opacity-80">Buy up</span>
          </button>

          <button
            type="button"
            disabled={!canTrade}
            onClick={() => void handleExecute('put')}
            className="flex flex-col items-center justify-center rounded-lg bg-[#fe7453] px-4 py-5 text-white shadow-lg shadow-[#fe7453]/20 transition hover:bg-[#ff8b6f] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isExecuting ? <Loader2 className="mb-1 animate-spin" size={24} /> : <ArrowDownRight size={26} className="mb-1" />}
            <span className="text-sm font-black tracking-wide">PUT</span>
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] opacity-80">Sell down</span>
          </button>
        </div>

        <div className="rounded-xl border border-white/5 bg-[#212127] px-4 py-3">
          <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">
            <span>Account balance</span>
            <span>{sessionConnected ? 'Live' : 'Disconnected'}</span>
          </div>
          <p className="mt-1 text-xl font-black text-[#e3e6e7]">${Number(balance || 0).toFixed(2)}</p>
        </div>

        {tradeError && (
          <div className="flex items-start gap-2 rounded-xl border border-[#fe7453]/30 bg-[#3f1d00] px-4 py-3 text-[#ff9b82]">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            <p className="text-sm">{tradeError}</p>
          </div>
        )}

        {lastTradeResult && (
          <div className="rounded-xl border border-white/5 bg-[#212127] px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">Last trade</p>
            <p className="mt-1 text-sm font-bold text-[#e3e6e7]">
              {lastTradeResult.outcome ? lastTradeResult.outcome.toUpperCase() : 'RECORDED'}
            </p>
            <p className="text-xs text-gray-500">
              {typeof lastTradeResult.pnl === 'number' ? `P&L ${lastTradeResult.pnl > 0 ? '+' : ''}${lastTradeResult.pnl.toFixed(2)}` : 'Result captured'}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
