import React from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle2, Zap } from 'lucide-react';

export default function AssetManipulationStats({ stats }) {
  const manip = stats?.manipulation || {};
  const leaderboard = manip?.leaderboard || [];
  const cleanWr = manip?.global_clean_win_rate ?? 0;
  const manipWr = manip?.global_manipulated_win_rate ?? 0;
  const totalClean = manip?.total_clean_trades ?? 0;
  const totalManip = manip?.total_manipulated_trades ?? 0;

  return (
    <div className="p-4 rounded-xl bg-[#15181e] border border-white/5 shadow-lg flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <ShieldAlert size={16} />
            </div>
            <div>
              <h3 className="text-xs font-black uppercase tracking-wider text-white">Asset Manipulation & Microstructure</h3>
              <p className="text-[9px] font-semibold text-gray-400">Hazardous Asset Detection & Trap Impact</p>
            </div>
          </div>

          {/* Clean vs Manipulated WR Summary */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-[9px] font-bold text-emerald-400">
              <CheckCircle2 size={10} />
              <span>Clean: {cleanWr.toFixed(1)}% ({totalClean})</span>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20 text-[9px] font-bold text-rose-400">
              <AlertTriangle size={10} />
              <span>Trapped: {manipWr.toFixed(1)}% ({totalManip})</span>
            </div>
          </div>
        </div>

        {/* Asset Table / Leaderboard */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[10px]">
            <thead>
              <tr className="text-gray-400 uppercase tracking-wider text-[8px] border-b border-white/5 pb-1">
                <th className="py-1.5 font-bold">Asset</th>
                <th className="py-1.5 font-bold">Manip Freq</th>
                <th className="py-1.5 font-bold">Dominant Pattern</th>
                <th className="py-1.5 font-bold">Clean WR</th>
                <th className="py-1.5 font-bold">Trapped WR</th>
                <th className="py-1.5 font-bold text-right">Hazard Level</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono">
              {leaderboard.slice(0, 8).map((a) => {
                const isHigh = a.danger_level === 'HIGH';
                const isMod = a.danger_level === 'MODERATE';
                const badgeColor = isHigh
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                  : isMod
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                  : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';

                return (
                  <tr key={a.asset} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-2 font-bold text-white flex items-center gap-1.5 font-sans">
                      <span>{a.asset}</span>
                      <span className="text-[8px] text-gray-500 font-mono">({a.total_trades})</span>
                    </td>
                    <td className="py-2 text-gray-300">
                      <span className={a.manipulation_freq_pct > 20 ? 'text-rose-400 font-bold' : ''}>
                        {a.manipulation_freq_pct.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-2 text-gray-400 font-sans">
                      {a.dominant_manipulation_type !== 'None' ? (
                        <span className="px-1.5 py-0.5 rounded bg-white/5 text-[9px] text-gray-300">
                          {a.dominant_manipulation_type}
                        </span>
                      ) : (
                        <span className="text-gray-600">Clean</span>
                      )}
                    </td>
                    <td className="py-2">
                      <span className={a.clean_win_rate >= 50 ? 'text-emerald-400 font-bold' : 'text-rose-400'}>
                        {a.clean_trades > 0 ? `${a.clean_win_rate.toFixed(1)}%` : '--'}
                      </span>
                    </td>
                    <td className="py-2">
                      <span className={a.manipulated_win_rate >= 50 ? 'text-emerald-400' : 'text-rose-400 font-bold'}>
                        {a.manipulated_trades > 0 ? `${a.manipulated_win_rate.toFixed(1)}%` : '--'}
                      </span>
                    </td>
                    <td className="py-2 text-right">
                      <span className={`px-2 py-0.5 rounded text-[8px] font-black uppercase border ${badgeColor}`}>
                        {a.danger_level}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {leaderboard.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-gray-500 font-sans text-[10px]">
                    No trade manipulation data in selected scope.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
