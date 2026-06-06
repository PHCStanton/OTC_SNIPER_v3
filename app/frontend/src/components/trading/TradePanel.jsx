/**
 * TradePanel — execution controls for the Phase 5 trading workspace.
 * Redesigned to follow the Stitch Design Reference.
 */
import { useMemo } from 'react';
import { ArrowDownRight, ArrowUpRight, AlertTriangle, DollarSign, Loader2, Wallet } from 'lucide-react';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { resolveTradeStake, useTradingStore } from '../../stores/useTradingStore.js';
import { formatAssetLabel } from './chartUtils.js';

export default function TradePanel() {
  const { selectedAsset } = useAssetStore();
  const { sessionStatus, balance, accountType } = useOpsStore();
  const {
    amount,
    amountType,
    duration,
    isExecuting,
    tradeError,
    setAmount,
    setAmountType,
    setDuration,
    setDirection,
    executeTrade,
  } = useTradingStore();

  const sessionConnected = sessionStatus === 'connected';
  const broker = 'pocket_option';

  const calculatedStake = useMemo(() => {
    return resolveTradeStake({ amount, amountType, balance });
  }, [amount, amountType, balance]);

  const parsedDuration = useMemo(() => {
    const value = Number(duration);
    return Number.isFinite(value) ? value : 0;
  }, [duration]);

  const canTrade = sessionConnected && !isExecuting && calculatedStake > 0 && parsedDuration > 0;

  async function handleExecute(direction) {
    if (!sessionConnected || isExecuting || calculatedStake <= 0 || parsedDuration <= 0) return;
    setDirection(direction);
    await executeTrade(broker, selectedAsset);
  }

  return (
    <section className="flex h-full flex-col rounded-[20px] bg-[#1a1c22] p-6 shadow-xl border border-white/5">
      <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-4">
        <div>
          <p className="text-[10px] font-black uppercase tracking-widest text-[#ffb800]">Execution Panel</p>
          <h3 className="mt-1 text-md font-black uppercase tracking-wider text-white">{formatAssetLabel(selectedAsset)}</h3>
        </div>
        <span className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[9px] font-black uppercase tracking-widest ${
          sessionConnected 
            ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400' 
            : 'border-white/5 bg-[#25282f]/30 text-gray-500'
        }`}>
          <DollarSign size={10} />
          {accountType ? accountType.toUpperCase() : 'NO SESSION'}
        </span>
      </div>

      <div className="mt-6 space-y-6 flex-1 flex flex-col justify-between">
        <div className="space-y-5">
          {/* Trade Amount */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[10px] font-black uppercase tracking-widest text-gray-500">Trade Amount</label>
              <div className="flex bg-[#25282f]/50 border border-white/5 rounded-md p-0.5">
                <button
                  className={`px-2 py-0.5 text-[10px] font-black rounded transition-all ${amountType === '$' ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/25' : 'text-gray-500 hover:text-gray-300'}`}
                  onClick={() => setAmountType('$')}
                >
                  $
                </button>
                <button
                  className={`px-2 py-0.5 text-[10px] font-black rounded transition-all ${amountType === '%' ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/25' : 'text-gray-500 hover:text-gray-300'}`}
                  onClick={() => setAmountType('%')}
                >
                  %
                </button>
              </div>
            </div>
            
            <div className="flex h-14 w-full items-center overflow-hidden rounded-lg bg-white shadow-inner">
              <div className="flex h-full w-12 items-center justify-center bg-gray-50 text-gray-400 border-r border-gray-100">
                <DollarSign size={18} />
              </div>
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={amount}
                onChange={(event) => setAmount(Number(event.target.value))}
                className="h-full flex-1 px-4 text-xl font-black text-black outline-none"
              />
              {amountType === '%' ? (
                <div className="flex h-full items-center bg-gray-100 px-4 text-[10px] font-black uppercase tracking-widest text-gray-500 border-l border-gray-200">
                  = ${calculatedStake.toFixed(2)}
                </div>
              ) : (
                <div className="flex h-full items-center bg-gray-50 text-gray-400 border-l border-gray-100 px-4">
                  <Wallet size={16} />
                </div>
              )}
            </div>
          </div>

          {/* Expiration */}
          <div className="space-y-2">
            <label className="block text-[10px] font-black uppercase tracking-widest text-gray-500">Expiration</label>
            <div className="flex h-14 w-full items-center overflow-hidden rounded-lg bg-white shadow-inner">
              <div className="flex h-full w-12 items-center justify-center bg-gray-50 text-gray-400 border-r border-gray-100">
                <span className="text-lg font-black">#</span>
              </div>
              <input
                type="number"
                min="5"
                step="1"
                value={duration}
                onChange={(event) => setDuration(Number(event.target.value))}
                className="h-full flex-1 px-4 text-xl font-black text-black outline-none"
              />
              <div className="flex h-full items-center bg-gray-100 px-4 text-[10px] font-black uppercase tracking-widest text-gray-500 border-l border-gray-200">
                SEC
              </div>
            </div>

            <div className="grid grid-cols-5 gap-1.5 pt-1">
              {[5, 15, 30, 45, 60, 120, 300, 600, 900, 1800].map((val) => {
                const label = val >= 60 ? `${val / 60}M` : `${val}S`;
                return (
                  <button
                    key={val}
                    onClick={() => setDuration(val)}
                    className={`rounded-md border py-2 text-[10px] font-black tracking-widest text-center transition-all duration-200 ${
                      duration === val 
                        ? 'border-[#ffb800]/30 bg-[#ffb800]/10 text-[#ffb800]' 
                        : 'border-white/5 bg-[#25282f]/30 text-gray-500 hover:text-white hover:border-white/10'
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="space-y-4 pt-4">
          {/* Action Triggers */}
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              disabled={!canTrade}
              onClick={() => void handleExecute('call')}
              className="flex flex-col items-center justify-center rounded-xl bg-emerald-500 py-5 text-black hover:bg-emerald-400 active:scale-98 transition disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-emerald-500"
            >
              {isExecuting ? <Loader2 className="mb-1 animate-spin" size={24} /> : <ArrowUpRight size={28} className="mb-1" />}
              <span className="text-sm font-black tracking-widest uppercase">CALL</span>
              <span className="text-[9px] font-bold uppercase tracking-widest opacity-60">Buy Up</span>
            </button>

            <button
              type="button"
              disabled={!canTrade}
              onClick={() => void handleExecute('put')}
              className="flex flex-col items-center justify-center rounded-xl bg-rose-500 py-5 text-white hover:bg-rose-400 active:scale-98 transition disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-rose-500"
            >
              {isExecuting ? <Loader2 className="mb-1 animate-spin" size={24} /> : <ArrowDownRight size={28} className="mb-1" />}
              <span className="text-sm font-black tracking-widest uppercase">PUT</span>
              <span className="text-[9px] font-bold uppercase tracking-widest opacity-80">Sell Down</span>
            </button>
          </div>

          {tradeError && (
            <div className="flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-4 text-red-300">
              <AlertTriangle size={18} className="shrink-0 text-red-400" />
              <p className="text-xs font-semibold uppercase tracking-wider">{tradeError}</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
