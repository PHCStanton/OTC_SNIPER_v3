import React from 'react';
import { History } from 'lucide-react';

export default function TradeHistoryTable({ ghostTrades }) {
  return (
    <div className="bg-[#141818] border border-white/5 rounded-xl overflow-hidden flex flex-col flex-1 min-h-[300px]">
      <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between">
        <h3 className="text-sm font-bold text-gray-400 flex items-center gap-2 uppercase tracking-wider">
          <History size={16} className="text-[#f5df19]" />
          Recent Ghost Activity
        </h3>
        <span className="text-[10px] bg-white/5 text-gray-500 px-2 py-0.5 rounded-full font-bold">
          Last 50 trades
        </span>
      </div>
      <div className="overflow-x-auto flex-1 custom-scrollbar">
        <table className="w-full text-left text-xs">
          <thead className="bg-white/[0.02] text-gray-500 font-bold uppercase tracking-wider sticky top-0">
            <tr>
              <th className="px-5 py-3 border-b border-white/5">Asset</th>
              <th className="px-5 py-3 border-b border-white/5">Time</th>
              <th className="px-5 py-3 border-b border-white/5">OTEO</th>
              <th className="px-5 py-3 border-b border-white/5">Outcome</th>
              <th className="px-5 py-3 border-b border-white/5 text-right">Profit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {ghostTrades.length > 0 ? (
              ghostTrades.slice(-50).reverse().map((trade, idx) => (
                <tr key={trade.id || idx} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="px-5 py-3 font-bold text-gray-300">{trade.asset || 'AUDCAD_otc'}</td>
                  <td className="px-5 py-3 text-gray-500">
                    {new Date(trade.createdAt || Date.now()).toLocaleTimeString()}
                  </td>
                  <td className="px-5 py-3">
                    <span className="px-2 py-0.5 rounded bg-[#f5df19]/10 text-[#f5df19] font-black">
                      {trade.oteo_score || '--'}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-0.5 rounded font-bold uppercase ${
                      trade.outcome === 'win' ? 'bg-emerald-400/10 text-emerald-400' : 
                      trade.outcome === 'loss' ? 'bg-rose-400/10 text-rose-400' : 'bg-gray-400/10 text-gray-400'
                    }`}>
                      {trade.outcome}
                    </span>
                  </td>
                  <td className={`px-5 py-3 text-right font-bold ${
                    trade.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}>
                    {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="5" className="px-5 py-10 text-center text-gray-600 italic">
                  No ghost trades recorded in this session yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}