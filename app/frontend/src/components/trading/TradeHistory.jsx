/**
 * TradeHistory — recent trade table for the Phase 5 trading workspace.
 */
import { useEffect } from 'react';
import { ArrowDownRight, ArrowUpRight, RotateCcw } from 'lucide-react';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { useTradingStore } from '../../stores/useTradingStore.js';
import { formatAssetLabel, formatPrice } from './chartUtils.js';

export default function TradeHistory() {
  const { sessionStatus } = useOpsStore();
  const { trades, isLoadingTrades, tradeError, loadTrades } = useTradingStore();

  useEffect(() => {
    if (sessionStatus === 'connected') {
      void loadTrades('pocket_option');
    }
  }, [sessionStatus, loadTrades]);

  return (
    <section className="rounded-xl border border-white/5 bg-[#1a1717] p-4 shadow-2xl shadow-black/30 backdrop-blur">
      <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-500">Logs</p>
          <h3 className="text-lg font-black tracking-tight text-[#e3e6e7]">Recent trades</h3>
        </div>

        <button
          type="button"
          onClick={() => void loadTrades('pocket_option')}
          className="flex items-center gap-2 rounded-full border border-white/5 bg-[#212127] px-3 py-1.5 text-xs font-semibold text-[#e3e6e7] transition hover:bg-[#282d2e]"
        >
          <RotateCcw size={12} />
          Refresh
        </button>
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
              <th className="px-3 py-2">Time</th>
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
                  Loading trade history…
                </td>
              </tr>
            )}

            {!isLoadingTrades && trades.length === 0 && (
              <tr>
                <td className="px-3 py-6 text-center text-gray-500" colSpan={6}>
                  No trades recorded yet.
                </td>
              </tr>
            )}

            {trades.slice(0, 8).map((trade, index) => {
              const outcome = typeof trade.outcome === 'string' ? trade.outcome.toLowerCase() : '';
              const direction = typeof trade.direction === 'string' ? trade.direction.toLowerCase() : '';
              const time = trade.created_at || trade.timestamp || trade.time || '—';
              const asset = trade.asset || trade.symbol || '—';
              const amount = Number(trade.amount);
              const payout = Number(trade.payout ?? trade.profit ?? trade.pnl);
              const status = trade.status || outcome || 'recorded';

              return (
                <tr key={`${asset}-${time}-${index}`} className="transition hover:bg-white/5">
                  <td className="whitespace-nowrap px-3 py-2 text-xs text-gray-500">{time}</td>
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
                  <td className="whitespace-nowrap px-3 py-2 text-right">
                    <span className="rounded-full bg-[#212127] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-400">
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
