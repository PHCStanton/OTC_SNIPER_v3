import React, { useState } from 'react';
import { History, Activity } from 'lucide-react';
import TradeDetailsModal from '../trading/TradeDetailsModal.jsx';

export default function TradeHistoryTable({ ghostTrades }) {
  const [selectedTrade, setSelectedTrade] = useState(null);
  const formatTradeTime = (trade) => {
    const timestamp = Number(trade.entryTime ?? trade.exitTime);
    if (Number.isFinite(timestamp) && timestamp > 0) {
      return new Date(timestamp * 1000).toLocaleTimeString();
    }
    return new Date(trade.createdAt || Date.now()).toLocaleTimeString();
  };

  const formatOteoScore = (score) => {
    const numericScore = Number(score);
    return Number.isFinite(numericScore) ? numericScore.toFixed(1) : '--';
  };

  const formatProfit = (pnl) => {
    const numericPnl = Number(pnl);
    return Number.isFinite(numericPnl) ? `${numericPnl >= 0 ? '+' : ''}${numericPnl.toFixed(2)}` : '--';
  };

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
              <th className="px-5 py-3 border-b border-white/5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {ghostTrades.length > 0 ? (
              ghostTrades.slice(-50).reverse().map((trade, idx) => (
                <tr 
                  key={trade.id || idx} 
                  className="hover:bg-white/[0.02] transition-colors group cursor-pointer"
                  onClick={() => setSelectedTrade({ ...trade, kind: 'ghost' })}
                >
                  <td className="px-5 py-3 font-bold text-gray-300">{trade.asset || '—'}</td>
                  <td className="px-5 py-3 text-gray-500">
                    {formatTradeTime(trade)}
                  </td>
                  <td className="px-5 py-3">
                    <span className="px-2 py-0.5 rounded bg-[#f5df19]/10 text-[#f5df19] font-black">
                      {formatOteoScore(trade.oteo_score)}
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
                    {formatProfit(trade.pnl)}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedTrade({ ...trade, kind: 'ghost' });
                      }}
                      className="text-[#ffb800]/60 hover:text-[#ffb800] bg-[#ffb800]/5 hover:bg-[#ffb800]/20 p-1.5 rounded transition-colors" 
                      title="AI Analysis"
                    >
                      <Activity size={12} />
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="6" className="px-5 py-10 text-center text-gray-600 italic">
                  No ghost trades recorded in this session yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedTrade && (
        <TradeDetailsModal trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
      )}
    </div>
  );
}