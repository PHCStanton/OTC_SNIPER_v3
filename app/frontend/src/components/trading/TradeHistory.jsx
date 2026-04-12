/**
 * TradeHistory — recent trade table for the Phase 5 trading workspace.
 */
import { useEffect, useState } from 'react';
import { ArrowDownRight, ArrowUpRight, RotateCcw, Activity, Ghost, User } from 'lucide-react';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { useTradingStore } from '../../stores/useTradingStore.js';
import { formatAssetLabel, formatPrice } from './chartUtils.js';
import TradeDetailsModal from './TradeDetailsModal.jsx';

export default function TradeHistory() {
  const { sessionStatus } = useOpsStore();
  const { trades, isLoadingTrades, tradeError, loadTrades, tradeHistoryMode, setTradeHistoryMode } = useTradingStore();
  
  const [selectedTrade, setSelectedTrade] = useState(null);

  useEffect(() => {
    if (sessionStatus === 'connected') {
      void loadTrades('pocket_option');
    }
  }, [sessionStatus, loadTrades]);

  const recentTrades = [...trades].reverse().slice(0, 8);

  return (
    <section className="rounded-xl border border-white/5 bg-[#1a1717] p-4 shadow-2xl shadow-black/30 backdrop-blur">
      <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-500">Logs</p>
          <h3 className="text-lg font-black tracking-tight text-[#e3e6e7]">Recent trades</h3>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex bg-[#212127] rounded-full p-0.5 border border-white/5">
            <button
              onClick={() => setTradeHistoryMode('live')}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-wider transition-colors ${tradeHistoryMode === 'live' ? 'bg-[#f5df19]/10 text-[#f5df19]' : 'text-gray-500 hover:text-gray-300'}`}
            >
              <User size={10} /> Live
            </button>
            <button
              onClick={() => setTradeHistoryMode('ghost')}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-wider transition-colors ${tradeHistoryMode === 'ghost' ? 'bg-indigo-500/10 text-indigo-400' : 'text-gray-500 hover:text-gray-300'}`}
            >
              <Ghost size={10} /> Ghost
            </button>
          </div>

          <button
            type="button"
            onClick={() => void loadTrades('pocket_option')}
            disabled={isLoadingTrades}
            className="flex items-center gap-2 rounded-full border border-white/5 bg-[#212127] px-3 py-1.5 text-xs font-semibold text-[#e3e6e7] transition hover:bg-[#282d2e] disabled:opacity-50"
          >
            <RotateCcw size={12} className={isLoadingTrades ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {tradeError && (
        <div className="mt-3 rounded-xl border border-[#fe7453]/30 bg-[#3f1d00] px-3 py-2 text-sm text-[#ff9b82]">
          {tradeError}
        </div>
      )}

      <div className="mt-3 overflow-hidden rounded-xl border border-white/5">
        <table className="min-w-full divide-y divide-white/5 text-left text-sm">
          <thead className="bg-[#212127] text-[10px] font-semibold uppercase tracking-[0.2em] text-gray-500">
            <tr>
              <th className="px-3 py-2">Time (UTC)</th>
              <th className="px-3 py-2">Asset</th>
              <th className="px-3 py-2">Direction</th>
              <th className="px-3 py-2 text-right">Amount</th>
              <th className="px-3 py-2 text-right">Payout</th>
              <th className="px-3 py-2 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 bg-[#1a1717]">
            {isLoadingTrades && trades.length === 0 && (
              <tr>
                <td className="px-3 py-6 text-center text-gray-500" colSpan={6}>
                  <RotateCcw className="inline animate-spin mb-1 mr-2" size={14} /> Loading trade history…
                </td>
              </tr>
            )}

            {!isLoadingTrades && trades.length === 0 && (
              <tr>
                <td className="px-3 py-6 text-center text-gray-500" colSpan={6}>
                  No trades recorded for {tradeHistoryMode} session yet.
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
                  className="transition hover:bg-white/5 cursor-pointer"
                  onClick={() => setSelectedTrade({ ...trade, kind: tradeHistoryMode })}
                >
                  <td className="whitespace-nowrap px-3 py-2 text-xs text-gray-500 font-mono">{time}</td>
                  <td className="whitespace-nowrap px-3 py-2 font-semibold text-[#e3e6e7]">
                    {formatAssetLabel(asset)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] ${direction === 'put' || direction === 'sell' ? 'bg-[#fe7453]/10 text-[#fe7453]' : 'bg-emerald-500/10 text-emerald-400'}`}>
                      {direction === 'put' || direction === 'sell' ? <ArrowDownRight size={10} /> : <ArrowUpRight size={10} />}
                      {direction || '—'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right text-gray-300">
                    {Number.isFinite(amount) ? `$${amount.toFixed(2)}` : '—'}
                  </td>
                  <td className={`whitespace-nowrap px-3 py-2 text-right font-semibold ${Number.isFinite(payout) && payout > 0 ? 'text-emerald-400' : Number.isFinite(payout) && payout < 0 ? 'text-[#fe7453]' : 'text-gray-500'}`}>
                    {Number.isFinite(payout) ? `${payout > 0 ? '+' : ''}$${Math.abs(payout).toFixed(2)}` : '—'}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right flex items-center justify-end gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] ${outcome === 'win' ? 'text-emerald-400 bg-emerald-400/10 border border-emerald-400/20' : outcome === 'loss' ? 'text-red-400 bg-red-400/10 border border-red-400/20' : 'bg-[#212127] text-gray-400'}`}>
                      {status}
                    </span>
                    <button className="text-[#f5df19]/60 hover:text-[#f5df19] bg-[#f5df19]/5 hover:bg-[#f5df19]/20 p-1 rounded transition-colors" title="AI Analysis">
                       <Activity size={12} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selectedTrade && (
        <TradeDetailsModal trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
      )}
    </section>
  );
}
