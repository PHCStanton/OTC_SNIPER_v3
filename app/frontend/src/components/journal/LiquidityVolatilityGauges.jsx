import React, { useState } from 'react';
import { Activity, Gauge, Flame, Sparkles, ToggleLeft, ToggleRight } from 'lucide-react';

// Map the raw ATR band labels to their % equivalents (ATR × 100)
const VOL_PCT_LABELS = {
  'Ultra-Low (<0.0002)':     'Ultra-Low (<0.02%)',
  'Optimal (0.0002-0.0006)': 'Optimal (0.02%-0.06%)',
  'High (0.0006-0.0012)':   'High (0.06%-0.12%)',
  'Extreme (>0.0012)':      'Extreme (>0.12%)',
};

export default function LiquidityVolatilityGauges({ stats }) {
  const [showVolPct, setShowVolPct] = useState(false);

  const volBands = stats?.volatility?.bands || [];
  const volSweetSpot = stats?.volatility?.sweet_spot || 'Optimal (0.0002-0.0006)';

  const liqBands = stats?.liquidity?.bands || [];
  const liqSweetSpot = stats?.liquidity?.sweet_spot || 'Balanced (80-150/min)';

  // Total trades across all liquidity bands (for % share calculation)
  const totalLiqTrades = liqBands.reduce((sum, b) => sum + (b.trades || 0), 0);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* ── Volatility Distribution Card ── */}
      <div className="p-4 rounded-xl bg-[#15181e] border border-white/5 flex flex-col justify-between shadow-lg">
        <div>
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/5">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Flame size={16} />
              </div>
              <div>
                <h3 className="text-xs font-black uppercase tracking-wider text-white">Volatility Profile</h3>
                <p className="text-[9px] font-semibold text-gray-400">ATR Range Distribution & Edge</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Decimal / % toggle */}
              <button
                onClick={() => setShowVolPct(p => !p)}
                className={`flex items-center gap-1 px-2 py-0.5 rounded-full border text-[9px] font-black transition-all ${
                  showVolPct
                    ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                    : 'bg-white/5 border-white/10 text-gray-400 hover:text-white'
                }`}
                title={showVolPct ? 'Show decimal values' : 'Show percentage values'}
              >
                {showVolPct ? <ToggleRight size={11} /> : <ToggleLeft size={11} />}
                <span>{showVolPct ? '%' : '0.00x'}</span>
              </button>

              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-[9px] font-bold text-amber-400">
                <Sparkles size={10} />
                <span>Sweet Spot: {volSweetSpot.split(' ')[0]}</span>
              </div>
            </div>
          </div>

          {/* Volatility Bands */}
          <div className="space-y-2.5">
            {volBands.map((b) => {
              const wr = b.win_rate || 0;
              const isSweet = b.is_sweet_spot;
              const barColor = isSweet
                ? 'bg-gradient-to-r from-amber-500 to-emerald-400'
                : wr >= 55
                ? 'bg-emerald-500'
                : wr >= 45
                ? 'bg-amber-500'
                : 'bg-rose-500';

              const displayLabel = showVolPct
                ? (VOL_PCT_LABELS[b.band] || b.band)
                : b.band;

              return (
                <div key={b.band} className={`p-2 rounded-lg border transition-all ${isSweet ? 'bg-amber-500/5 border-amber-500/30' : 'bg-black/20 border-white/5'}`}>
                  <div className="flex items-center justify-between text-[10px] mb-1">
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-gray-200">{displayLabel}</span>
                      {isSweet && (
                        <span className="px-1.5 py-0.2 rounded text-[8px] font-black uppercase bg-amber-500 text-black">
                          Optimal
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-gray-400 font-mono">{b.trades} trades</span>
                      <span className={`font-mono font-bold ${wr >= 50 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {wr.toFixed(1)}% WR
                      </span>
                      <span className={`font-mono text-[9px] ${b.total_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        ${b.total_profit >= 0 ? '+' : ''}{b.total_profit.toFixed(1)}
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
          </div>
        </div>
      </div>

      {/* ── Liquidity Distribution Card ── */}
      <div className="p-4 rounded-xl bg-[#15181e] border border-white/5 flex flex-col justify-between shadow-lg">
        <div>
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/5">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <Activity size={16} />
              </div>
              <div>
                <h3 className="text-xs font-black uppercase tracking-wider text-white">Liquidity Gauge</h3>
                <p className="text-[9px] font-semibold text-gray-400">Tick Frequency & Speed Distribution</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-[9px] font-bold text-cyan-400">
              <Gauge size={10} />
              <span>Sweet Spot: {liqSweetSpot.split(' ')[0]}</span>
            </div>
          </div>

          {/* Liquidity Bands */}
          <div className="space-y-2.5">
            {liqBands.map((b) => {
              const wr = b.win_rate || 0;
              const isSweet = b.is_sweet_spot;
              const barColor = isSweet
                ? 'bg-gradient-to-r from-cyan-500 to-emerald-400'
                : wr >= 55
                ? 'bg-emerald-500'
                : wr >= 45
                ? 'bg-amber-500'
                : 'bg-rose-500';

              const tradePct = totalLiqTrades > 0
                ? ((b.trades / totalLiqTrades) * 100).toFixed(1)
                : '0.0';

              return (
                <div key={b.band} className={`p-2 rounded-lg border transition-all ${isSweet ? 'bg-cyan-500/5 border-cyan-500/30' : 'bg-black/20 border-white/5'}`}>
                  <div className="flex items-center justify-between text-[10px] mb-1">
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-gray-200">{b.band}</span>
                      {isSweet && (
                        <span className="px-1.5 py-0.2 rounded text-[8px] font-black uppercase bg-cyan-400 text-black">
                          Optimal
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-gray-400 font-mono">{b.trades} trades</span>
                      {/* Trade share percentage badge */}
                      <span
                        className="px-1.5 py-0.5 rounded-full bg-white/5 border border-white/10 font-mono text-[9px] text-cyan-300"
                        title={`${tradePct}% of total trades occurred in this liquidity band`}
                      >
                        {tradePct}%
                      </span>
                      <span className={`font-mono font-bold ${wr >= 50 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {wr.toFixed(1)}% WR
                      </span>
                      <span className={`font-mono text-[9px] ${b.total_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        ${b.total_profit >= 0 ? '+' : ''}{b.total_profit.toFixed(1)}
                      </span>
                    </div>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                      style={{ width: `${Math.min(100, wr)}%` }}
                    />
                  </div>
                  {/* Trade distribution sub-bar */}
                  <div className="w-full h-0.5 rounded-full bg-white/5 overflow-hidden mt-1">
                    <div
                      className="h-full rounded-full bg-cyan-500/40 transition-all duration-700"
                      style={{ width: `${tradePct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Total trades footer */}
          {totalLiqTrades > 0 && (
            <p className="text-[9px] text-gray-600 font-mono mt-2.5 text-right">
              Total: {totalLiqTrades} trades across all bands
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
