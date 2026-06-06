/**
 * TradeHistory — recent trade table for the Phase 5 trading workspace.
 * Redesigned to follow the Stitch Design Reference.
 */
import { useEffect } from 'react';
import { ArrowDownRight, ArrowUpRight, RotateCcw, Ghost, User } from 'lucide-react';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { useTradingStore } from '../../stores/useTradingStore.js';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useToastStore } from '../../stores/useToastStore.js';
import { formatAssetLabel } from './chartUtils.js';

export default function TradeHistory() {
  const { sessionStatus } = useOpsStore();
  const { trades, isLoadingTrades, tradeError, loadTrades, tradeHistoryMode, setTradeHistoryMode } = useTradingStore();
  
  const handleSelectOrExecuteTrade = (trade) => {
    const asset = trade.asset || trade.symbol;
    if (!asset) return;

    const { autoGhostCopyMode } = useSettingsStore.getState();
    const assetLabel = asset.replace(/_otc$/i, ' OTC').replace(/_/g, '/').toUpperCase();

    // Select the asset
    useAssetStore.getState().setSelectedAsset(asset);

    useToastStore.getState().addToast({
      type: 'success',
      message: `Selected Asset: ${assetLabel}`,
      duration: 3000
    });

    if (autoGhostCopyMode === 'execute') {
      const direction = (trade.direction || 'call').toLowerCase();
      const rawDuration = Number(trade.expirationSeconds || trade.expiration_seconds || trade.duration || 60);

      useTradingStore.getState().setDirection(direction);
      useTradingStore.getState().setDuration(rawDuration);
      void useTradingStore.getState().executeTrade('pocket_option', asset);
    }
  };

  useEffect(() => {
    if (sessionStatus === 'connected') {
      void loadTrades('pocket_option');
    }
  }, [sessionStatus, loadTrades]);

  const recentTrades = [...trades].reverse().slice(0, 8);

  return (
    <section className="rounded-[20px] border border-white/5 bg-[#1a1c22] p-6 shadow-xl">
      <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-4">
        <div>
          <p className="text-[10px] font-black uppercase tracking-widest text-[#ffb800]">Audits & Logs</p>
          <h3 className="mt-1 text-md font-black uppercase tracking-wider text-white">Recent Transactions</h3>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex bg-[#25282f]/50 rounded-lg p-0.5 border border-white/5">
            <button
              onClick={() => setTradeHistoryMode('live')}
              className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-[9px] font-black uppercase tracking-widest transition-all duration-300 ${
                tradeHistoryMode === 'live' 
                  ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/25 shadow-sm' 
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              <User size={10} /> Live
            </button>
            <button
              onClick={() => setTradeHistoryMode('ghost')}
              className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-[9px] font-black uppercase tracking-widest transition-all duration-300 ${
                tradeHistoryMode === 'ghost' 
                  ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/25 shadow-sm' 
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              <Ghost size={10} /> Ghost
            </button>
          </div>

          <button
            type="button"
            onClick={() => void loadTrades('pocket_option')}
            disabled={isLoadingTrades}
            className="flex items-center gap-2 rounded-lg border border-white/5 bg-[#25282f] px-4 py-2 text-[10px] font-black uppercase tracking-widest text-gray-400 transition hover:bg-[#2d3139] hover:text-white disabled:opacity-40"
          >
            <RotateCcw size={12} className={isLoadingTrades ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {tradeError && (
        <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-red-300">
          {tradeError}
        </div>
      )}

      <div className="mt-4 overflow-hidden rounded-xl border border-white/5">
        <table className="min-w-full divide-y divide-white/5 text-left text-xs">
          <thead className="bg-[#25282f]/30 text-[9px] font-black uppercase tracking-widest text-gray-500">
            <tr>
              <th className="px-4 py-3">Timestamp (UTC)</th>
              <th className="px-4 py-3">Asset</th>
              <th className="px-4 py-3">Direction</th>
              <th className="px-4 py-3 text-right">Stake</th>
              <th className="px-4 py-3 text-right">Payout / PNL</th>
              <th className="px-4 py-3 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 bg-[#1a1c22]/10">
            {isLoadingTrades && trades.length === 0 && (
              <tr>
                <td className="px-4 py-8 text-center text-[10px] font-black uppercase tracking-widest text-gray-500" colSpan={6}>
                  <RotateCcw className="inline animate-spin mr-2" size={12} /> Syncing records...
                </td>
              </tr>
            )}

            {!isLoadingTrades && trades.length === 0 && (
              <tr>
                <td className="px-4 py-8 text-center text-[10px] font-black uppercase tracking-widest text-gray-500" colSpan={6}>
                  No active logs for {tradeHistoryMode} session.
                </td>
              </tr>
            )}

            {recentTrades.map((trade, index) => {
              const outcome = typeof trade.outcome === 'string' ? trade.outcome.toLowerCase() : '';
              const direction = typeof trade.direction === 'string' ? trade.direction.toLowerCase() : '';
              
              const rawTime = trade.created_at || trade.timestamp || trade.time;
              const time = rawTime ? new Date(Number(rawTime) * 1000).toISOString().replace("T", " ").substring(0, 19) : '—';
              
              const asset = trade.asset || trade.symbol || '—';
              const amount = Number(trade.amount);
              const payout = Number(trade.payout ?? trade.profit ?? trade.pnl);
              const status = trade.status || outcome || 'recorded';

              return (
                <tr 
                  key={`${asset}-${time}-${index}`} 
                  className="transition hover:bg-white/[0.02] cursor-pointer"
                  onClick={() => handleSelectOrExecuteTrade(trade)}
                >
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-500 font-mono">{time}</td>
                  <td className="whitespace-nowrap px-4 py-3 font-black text-white uppercase tracking-wider">
                    {formatAssetLabel(asset)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[9px] font-black uppercase tracking-widest ${
                      direction === 'put' || direction === 'sell' 
                        ? 'bg-rose-500/10 text-rose-400' 
                        : 'bg-emerald-500/10 text-emerald-400'
                    }`}>
                      {direction === 'put' || direction === 'sell' ? <ArrowDownRight size={10} /> : <ArrowUpRight size={10} />}
                      {direction || '—'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-gray-400 font-bold font-mono">
                    {Number.isFinite(amount) ? `$${amount.toFixed(2)}` : '—'}
                  </td>
                  <td className={`whitespace-nowrap px-4 py-3 text-right font-bold font-mono ${
                    Number.isFinite(payout) && payout > 0 
                      ? 'text-emerald-400' 
                      : Number.isFinite(payout) && payout < 0 
                        ? 'text-rose-400' 
                        : 'text-gray-500'
                  }`}>
                    {Number.isFinite(payout) ? `${payout > 0 ? '+' : ''}$${Math.abs(payout).toFixed(2)}` : '—'}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right flex items-center justify-end">
                    <span className={`rounded px-2 py-0.5 text-[9px] font-black uppercase tracking-widest ${
                      outcome === 'win' 
                        ? 'text-emerald-400 bg-emerald-400/10 border border-emerald-400/20' 
                        : outcome === 'loss' 
                          ? 'text-rose-400 bg-rose-400/10 border border-rose-400/20' 
                          : 'bg-[#25282f] text-gray-400'
                    }`}>
                      {status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
