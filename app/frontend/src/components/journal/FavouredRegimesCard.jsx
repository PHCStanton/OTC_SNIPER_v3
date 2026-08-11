import React, { useState } from 'react';
import { Compass, Check, ArrowRight, ShieldCheck, Sparkles } from 'lucide-react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';

export default function FavouredRegimesCard({ stats }) {
  const regimes = stats?.regimes || [];
  const [synced, setSynced] = useState(false);

  const updateSetting = useSettingsStore((s) => s.updateSetting);
  const ghostAllowedRegimes = useSettingsStore((s) => s.ghostAllowedRegimes || []);

  const favouredRegimesList = regimes
    .filter((r) => r.classification === 'FAVOURED' && r.regime !== 'UNKNOWN')
    .map((r) => r.regime);

  const handleSyncFavouredRegimes = () => {
    if (favouredRegimesList.length === 0) return;
    updateSetting('ghostAllowedRegimes', favouredRegimesList);
    setSynced(true);
    setTimeout(() => setSynced(false), 2500);
  };

  return (
    <div className="p-4 rounded-xl bg-[#15181e] border border-white/5 shadow-lg flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Compass size={16} />
            </div>
            <div>
              <h3 className="text-xs font-black uppercase tracking-wider text-white">Favoured Market Regimes</h3>
              <p className="text-[9px] font-semibold text-gray-400">Statistical Expectancy & Regime Whitelist</p>
            </div>
          </div>

          {favouredRegimesList.length > 0 && (
            <button
              onClick={handleSyncFavouredRegimes}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[9px] font-black uppercase tracking-wider transition-all border ${
                synced
                  ? 'bg-emerald-500 text-black border-emerald-400 shadow-md shadow-emerald-500/20'
                  : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25 hover:bg-emerald-500/20'
              }`}
            >
              {synced ? <Check size={11} /> : <Sparkles size={11} />}
              <span>{synced ? 'Applied to Ghost' : 'Apply Favoured to Ghost'}</span>
            </button>
          )}
        </div>

        {/* Regimes Ranked Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {regimes.map((r) => {
            const isFavoured = r.classification === 'FAVOURED';
            const isNeutral = r.classification === 'NEUTRAL';
            const isAvoid = r.classification === 'AVOID';

            const cardBorder = isFavoured
              ? 'border-emerald-500/30 bg-emerald-500/5'
              : isNeutral
              ? 'border-amber-500/20 bg-amber-500/5'
              : 'border-rose-500/20 bg-rose-500/5';

            const badgeBg = isFavoured
              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
              : isNeutral
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
              : 'bg-rose-500/20 text-rose-300 border-rose-500/30';

            const isCurrentlyAllowed = ghostAllowedRegimes.includes(r.regime);

            return (
              <div key={r.regime} className={`p-2.5 rounded-lg border flex flex-col justify-between ${cardBorder}`}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-bold text-white font-mono tracking-tight">{r.regime}</span>
                  <span className={`px-1.5 py-0.2 rounded text-[7px] font-black uppercase border ${badgeBg}`}>
                    {r.classification}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-1 text-[9px] font-mono mb-1.5">
                  <div>
                    <span className="text-gray-500 text-[7px] block uppercase">Win Rate</span>
                    <span className={`font-bold ${r.win_rate >= 50 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {r.win_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 text-[7px] block uppercase">Trades</span>
                    <span className="text-gray-300">{r.trades} ({r.wins}W)</span>
                  </div>
                  <div>
                    <span className="text-gray-500 text-[7px] block uppercase">Profit</span>
                    <span className={r.net_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                      ${r.net_profit >= 0 ? '+' : ''}{r.net_profit.toFixed(1)}
                    </span>
                  </div>
                </div>

                {isCurrentlyAllowed && (
                  <div className="flex items-center gap-1 text-[8px] text-gray-400 font-semibold pt-1 border-t border-white/5">
                    <ShieldCheck size={10} className="text-emerald-400" />
                    <span>Active in Ghost Protocol</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
