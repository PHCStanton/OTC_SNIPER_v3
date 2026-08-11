import React from 'react';
import { Clock, Zap, Target, Sparkles } from 'lucide-react';

export default function AdaptiveExpiriesCard({ stats }) {
  const expiries = stats?.expiries?.expiries || [];
  const bestDuration = stats?.expiries?.best_duration || 60;

  return (
    <div className="p-4 rounded-xl bg-[#15181e] border border-white/5 shadow-lg flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Clock size={16} />
            </div>
            <div>
              <h3 className="text-xs font-black uppercase tracking-wider text-white">Adaptive Expiries Performance</h3>
              <p className="text-[9px] font-semibold text-gray-400">Duration Success Rate & Contract Optimization</p>
            </div>
          </div>

          <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 text-[9px] font-bold text-indigo-300">
            <Sparkles size={10} />
            <span>Optimal: {bestDuration}s</span>
          </div>
        </div>

        {/* Expiry Bars */}
        <div className="space-y-2.5">
          {expiries.map((e) => {
            const isBest = e.is_best;
            const wr = e.win_rate || 0;
            const barColor = isBest
              ? 'bg-gradient-to-r from-indigo-500 to-emerald-400'
              : wr >= 55
              ? 'bg-emerald-500'
              : wr >= 45
              ? 'bg-amber-500'
              : 'bg-rose-500';

            return (
              <div
                key={e.duration_seconds}
                className={`p-2.5 rounded-lg border transition-all ${
                  isBest ? 'bg-indigo-500/5 border-indigo-500/30' : 'bg-black/20 border-white/5'
                }`}
              >
                <div className="flex items-center justify-between text-[10px] mb-1">
                  <div className="flex items-center gap-1.5 font-mono">
                    <span className="font-bold text-white text-xs">{e.label}</span>
                    <span className="text-gray-500 text-[9px]">({e.duration_seconds}s)</span>
                    {isBest && (
                      <span className="px-1.5 py-0.2 rounded text-[7px] font-black uppercase bg-indigo-500 text-white">
                        Top Performer
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 font-mono">
                    <span className="text-gray-400">{e.trades} trades</span>
                    <span className={`font-bold ${wr >= 50 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {wr.toFixed(1)}% WR
                    </span>
                    <span className={`text-[9px] ${e.total_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      ${e.total_profit >= 0 ? '+' : ''}{e.total_profit.toFixed(1)}
                    </span>
                  </div>
                </div>

                <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                    style={{ width: `${Math.min(100, wr)}%` }}
                  />
                </div>
              </div>
            );
          })}
          {expiries.length === 0 && (
            <div className="py-4 text-center text-gray-500 text-[10px]">
              No expiry statistics available in selected scope.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
