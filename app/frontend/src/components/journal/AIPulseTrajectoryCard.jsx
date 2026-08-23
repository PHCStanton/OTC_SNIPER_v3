import React from 'react';
import { Zap, Activity, Clock, ShieldAlert, Sparkles, ArrowRight, TrendingUp, AlertTriangle, CheckCircle2, Inbox } from 'lucide-react';

export default function AIPulseTrajectoryCard({ stats }) {
  const pulseStats = stats?.ai_pulse_trajectory || {
    total_trades: 0,
    clean_wins: 0,
    premature_expirations: 0,
    momentum_exhaustions: 0,
    structural_traps: 0,
    directional_fails: 0,
    win_rate: 0,
    horizon_recommendations: { '60s': 0, '300s': 0 },
    recent_trajectories: [],
  };

  const total = pulseStats.total_trades || 0;
  const premature = pulseStats.premature_expirations || 0;
  const exhaustion = pulseStats.momentum_exhaustions || 0;
  const traps = pulseStats.structural_traps || 0;
  const cleanWins = pulseStats.clean_wins || 0;
  const fails = pulseStats.directional_fails || 0;

  const rec60 = pulseStats.horizon_recommendations?.['60s'] || 0;
  const rec300 = pulseStats.horizon_recommendations?.['300s'] || 0;
  const primaryRecommendation = rec300 > rec60 ? 'Extend Horizon to 300s' : rec60 > 0 ? 'Clamp Horizon to 60s' : 'Horizon Balanced';

  return (
    <div className="p-4 rounded-xl bg-[#15181e] border border-white/5 shadow-lg flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Zap size={16} />
            </div>
            <div>
              <h3 className="text-xs font-black uppercase tracking-wider text-white flex items-center gap-1.5">
                <span>AI Pulse Trajectory Attribution</span>
                <span className="text-[7px] font-black uppercase text-cyan-300 bg-cyan-500/20 border border-cyan-400/30 rounded px-1 py-0.2">
                  Self-Reflective
                </span>
              </h3>
              <p className="text-[9px] font-semibold text-gray-400">Intermediate Checkpoints & Horizon Post-Mortem</p>
            </div>
          </div>

          <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-[9px] font-bold text-cyan-300">
            <Sparkles size={10} />
            <span>Rec: {total > 0 ? primaryRecommendation : 'Awaiting Data'}</span>
          </div>
        </div>

        {total === 0 ? (
          /* Empty State */
          <div className="py-8 px-4 rounded-lg bg-black/20 border border-white/5 flex flex-col items-center justify-center text-center">
            <div className="p-2 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 mb-2">
              <Inbox size={20} />
            </div>
            <span className="text-xs font-bold text-white mb-0.5">No AI Pulse Trajectories Recorded</span>
            <p className="text-[9px] text-gray-400 max-w-xs">
              AI Pulse trade executions will automatically populate 30s–300s checkpoint telemetry, MFE/MAE excursions, and post-mortem diagnostic attribution here.
            </p>
          </div>
        ) : (
          <>
            {/* Global Summary Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
              <div className="p-2 rounded-lg bg-black/20 border border-white/5 text-center">
                <span className="text-[8px] uppercase tracking-wider text-gray-500 font-semibold block">Pulse Trades</span>
                <span className="text-sm font-black font-mono text-white">{total}</span>
              </div>
              <div className="p-2 rounded-lg bg-black/20 border border-white/5 text-center">
                <span className="text-[8px] uppercase tracking-wider text-gray-500 font-semibold block">Pulse WR</span>
                <span className={`text-sm font-black font-mono ${pulseStats.win_rate >= 50 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {pulseStats.win_rate.toFixed(1)}%
                </span>
              </div>
              <div className="p-2 rounded-lg bg-black/20 border border-white/5 text-center">
                <span className="text-[8px] uppercase tracking-wider text-gray-500 font-semibold block">Premature (60s)</span>
                <span className="text-sm font-black font-mono text-amber-400">{premature}</span>
              </div>
              <div className="p-2 rounded-lg bg-black/20 border border-white/5 text-center">
                <span className="text-[8px] uppercase tracking-wider text-gray-500 font-semibold block">Exhaustion (300s)</span>
                <span className="text-sm font-black font-mono text-indigo-400">{exhaustion}</span>
              </div>
            </div>

            {/* Diagnostic Post-Mortem Cards */}
            <div className="space-y-2 mb-3">
              {/* Premature Expiration Case */}
              <div className="p-2.5 rounded-lg bg-[#1a1d24] border border-amber-500/20 flex items-center justify-between transition-colors duration-150 hover:bg-[#20242c] hover:border-amber-500/40">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    <Clock size={13} />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-bold text-white uppercase">Premature Expiry (60s Loss &rarr; 300s Win)</span>
                      <span className="text-[8px] font-mono text-amber-400 font-bold">{premature} cases</span>
                    </div>
                    <p className="text-[8px] text-gray-400">Direction correct, but trade expired before completing structural reversal.</p>
                  </div>
                </div>
                {premature > 0 && (
                  <span className="text-[7.5px] font-mono font-bold text-amber-300 bg-amber-500/15 border border-amber-400/30 px-1.5 py-0.5 rounded">
                    Extend to 300s
                  </span>
                )}
              </div>

              {/* Momentum Exhaustion Case */}
              <div className="p-2.5 rounded-lg bg-[#1a1d24] border border-indigo-500/20 flex items-center justify-between transition-colors duration-150 hover:bg-[#20242c] hover:border-indigo-500/40">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    <TrendingUp size={13} />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-bold text-white uppercase">Momentum Exhaustion (300s Loss &rarr; 60s Win)</span>
                      <span className="text-[8px] font-mono text-indigo-400 font-bold">{exhaustion} cases</span>
                    </div>
                    <p className="text-[8px] text-gray-400">Target price reached rapidly, but gave back profits before 300s.</p>
                  </div>
                </div>
                {exhaustion > 0 && (
                  <span className="text-[7.5px] font-mono font-bold text-indigo-300 bg-indigo-500/15 border border-indigo-400/30 px-1.5 py-0.5 rounded">
                    Clamp to 60s
                  </span>
                )}
              </div>

              {/* Structural Trap / Manipulation Case */}
              <div className="p-2.5 rounded-lg bg-[#1a1d24] border border-rose-500/20 flex items-center justify-between transition-colors duration-150 hover:bg-[#20242c] hover:border-rose-500/40">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    <ShieldAlert size={13} />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-bold text-white uppercase">Structural Trap / Liquidity Spike</span>
                      <span className="text-[8px] font-mono text-rose-400 font-bold">{traps} cases</span>
                    </div>
                    <p className="text-[8px] text-gray-400">Immediate adverse spike without any favorable price excursion (MAE &gt;&gt; MFE).</p>
                  </div>
                </div>
                {traps > 0 && (
                  <span className="text-[7.5px] font-mono font-bold text-rose-300 bg-rose-500/15 border border-rose-400/30 px-1.5 py-0.5 rounded">
                    Tighten Gate
                  </span>
                )}
              </div>
            </div>

            {/* Recent Trajectory Log Snapshot */}
            {pulseStats.recent_trajectories && pulseStats.recent_trajectories.length > 0 && (
              <div>
                <span className="text-[8.5px] uppercase font-mono tracking-wider text-gray-400 font-semibold block mb-1.5">
                  Recent Trajectory Checkpoints
                </span>
                <div className="space-y-1 max-h-32 overflow-y-auto pr-1">
                  {pulseStats.recent_trajectories.slice(-4).reverse().map((traj, idx) => {
                    const isWin = traj.outcome === 'win';
                    return (
                      <div key={traj.trade_id || idx} className="p-1.5 rounded bg-black/30 border border-white/5 flex items-center justify-between text-[8px] font-mono">
                        <div className="flex items-center gap-1.5">
                          <span className={`px-1 py-0.2 rounded font-bold ${isWin ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                            {isWin ? 'WIN' : 'LOSS'}
                          </span>
                          <span className="text-white font-bold">{traj.asset}</span>
                          <span className="text-gray-400">{traj.direction} ({traj.expiration_seconds}s)</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-emerald-400" title="Max Favorable Excursion">MFE: +{traj.mfe}</span>
                          <span className="text-rose-400" title="Max Adverse Excursion">MAE: -{traj.mae}</span>
                          <span className="text-gray-400 bg-white/5 px-1 rounded">{traj.attribution}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
