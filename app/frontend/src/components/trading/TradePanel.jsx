/**
 * TradePanel — execution controls for the Phase 5 trading workspace.
 */
import { useMemo, useState } from 'react';
import { ArrowDownRight, ArrowUpRight, AlertTriangle, DollarSign, Ghost, Loader2, Wallet } from 'lucide-react';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { useTradingStore } from '../../stores/useTradingStore.js';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { formatAssetLabel } from './chartUtils.js';

export default function TradePanel() {
  const { selectedAsset } = useAssetStore();
  const { sessionStatus, balance, accountType } = useOpsStore();
  const {
    amount,
    duration,
    isExecuting,
    tradeError,
    lastTradeResult,
    setAmount,
    setDuration,
    setDirection,
    executeTrade,
  } = useTradingStore();

  const { ghostAmount } = useSettingsStore();
  const [amountType, setAmountType] = useState('$');

  const sessionConnected = sessionStatus === 'connected';
  const broker = 'pocket_option';

  const parsedAmount = useMemo(() => {
    const value = Number(amount);
    return Number.isFinite(value) ? value : 0;
  }, [amount]);

  const calculatedStake = useMemo(() => {
    if (amountType === '$') return parsedAmount;
    if (amountType === '%') {
      const bal = Number(balance) || 0;
      return Number((bal * (parsedAmount / 100)).toFixed(2));
    }
    return 0;
  }, [amountType, parsedAmount, balance]);

  const parsedDuration = useMemo(() => {
    const value = Number(duration);
    return Number.isFinite(value) ? value : 0;
  }, [duration]);

  const canTrade = sessionConnected && !isExecuting && calculatedStake > 0 && parsedDuration > 0;

  async function handleExecute(direction) {
    if (!sessionConnected || isExecuting || calculatedStake <= 0 || parsedDuration <= 0) return;
    setDirection(direction);
    await executeTrade(broker, selectedAsset, calculatedStake);
  }

  return (
    <section className="flex h-full flex-col rounded-xl border border-white/5 bg-[#1a1717] p-4 shadow-2xl shadow-black/30 backdrop-blur">
      <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-500">Execution panel</p>
          <h3 className="text-lg font-black tracking-tight text-[#e3e6e7]">{formatAssetLabel(selectedAsset)}</h3>
        </div>
        <div className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${sessionConnected ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400' : 'border-white/5 bg-[#212127] text-gray-500'}`}>
          <DollarSign size={11} />
          {accountType ? accountType.toUpperCase() : 'NO SESSION'}
        </div>
      </div>

      <div className="mt-4 space-y-4">
        <div>
          <div className="mb-1 flex items-center justify-between">
            <label className="block text-[10px] font-bold uppercase tracking-[0.22em] text-gray-500">Trade amount</label>
            <div className="flex bg-[#212127] rounded border border-white/10 p-0.5">
              <button
                className={`px-2 py-0.5 text-xs font-bold rounded-sm transition-colors ${amountType === '$' ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'}`}
                onClick={() => setAmountType('$')}
              >
                $
              </button>
              <button
                className={`px-2 py-0.5 text-xs font-bold rounded-sm transition-colors ${amountType === '%' ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'}`}
                onClick={() => setAmountType('%')}
              >
                %
              </button>
            </div>
          </div>
          <div className="relative">
            <input
              type="number"
              min="0.1"
              step="0.1"
              value={amount}
              onChange={(event) => setAmount(Number(event.target.value))}
              className="w-full rounded-xl border border-white/10 bg-white px-4 py-3 pr-24 text-lg font-black text-black outline-none transition focus:border-[#f5df19] focus:bg-white"
            />
            <div className="absolute inset-y-0 right-3 flex items-center gap-2 text-gray-500">
              {amountType === '%' && (
                <span className="text-[10px] font-black text-[#6b7280] bg-gray-100 px-1.5 py-0.5 rounded border border-gray-200">
                  = ${calculatedStake.toFixed(2)}
                </span>
              )}
              <Wallet size={16} />
            </div>
          </div>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <label className="block text-[10px] font-bold uppercase tracking-[0.22em] text-gray-500">Expiration</label>
          </div>
          <div className="relative">
            <input
              type="number"
              min="5"
              step="1"
              value={duration}
              onChange={(event) => setDuration(Number(event.target.value))}
              className="w-full rounded-xl border border-white/10 bg-white px-4 py-3 text-base font-bold text-black outline-none transition focus:border-[#f5df19] focus:bg-white"
            />
            <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">Seconds</p>
          </div>
          <div className="mt-2 flex gap-1">
            {[5, 15, 30, 45, 60].map((val) => (
              <button
                key={val}
                onClick={() => setDuration(val)}
                className={`flex-1 rounded border py-1 text-xs font-bold transition-colors ${duration === val ? 'border-[#f5df19] bg-[#f5df19]/10 text-[#f5df19]' : 'border-white/5 bg-[#212127] text-gray-400 hover:bg-white/5'}`}
              >
                {val === 60 ? '1M' : `${val}s`}
              </button>
            ))}
          </div>
        </div>



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

        {tradeError && (
          <div className="flex items-start gap-2 rounded-xl border border-[#fe7453]/30 bg-[#3f1d00] px-4 py-3 text-[#ff9b82]">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            <p className="text-sm">{tradeError}</p>
          </div>
        )}
      </div>
    </section>
  );
}
