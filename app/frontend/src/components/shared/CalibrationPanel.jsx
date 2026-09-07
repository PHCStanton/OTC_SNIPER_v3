import { useEffect, useState } from 'react';
import { Activity, Square, Play } from 'lucide-react';
import { useCalibrationStore, isCalibrationLockedState } from '../../stores/useCalibrationStore.js';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useToastStore } from '../../stores/useToastStore.js';
import { startCalibration, stopCalibration, updateRuntimeStrategyConfig } from '../../api/strategyApi.js';

function formatClock(totalSec) {
  const sec = Math.max(0, Math.round(Number(totalSec) || 0));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

// Lifecycle header label (fix: getCalibrationStateLabel was referenced at the
// render site but never defined — crashed the panel via ErrorBoundary).
function getCalibrationStateLabel(running, draining, state) {
  if (running) return 'Calibrating…';
  if (draining) return 'Draining…';
  if (state === 'DONE') return 'Calibration Complete';
  if (state === 'ABORTED') return 'Calibration Aborted';
  return 'Calibration';
}

export default function CalibrationPanel() {
  const calib = useCalibrationStore();
  const durationMinutes = useSettingsStore((s) => s.autoGhostCalibrationDurationMinutes);
  const targetTrades = useSettingsStore((s) => s.autoGhostCalibrationTargetTrades);
  const setDurationMinutes = useSettingsStore((s) => s.setAutoGhostCalibrationDurationMinutes);
  const setTargetTrades = useSettingsStore((s) => s.setAutoGhostCalibrationTargetTrades);

  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(null);
  const [tickElapsed, setTickElapsed] = useState(calib.elapsedSeconds);

  const locked = calib.locked || isCalibrationLockedState(calib.state);
  const running = calib.state === 'RUNNING';
  const draining = calib.state === 'ANALYZING' || calib.state === 'PROPOSING';

  useEffect(() => {
    // R2-2 (M-6): authoritative status fetch on mount so a page reload during a
    // locked state shows CALIBRATING/badge immediately (no 5s poll blind window).
    void useCalibrationStore.getState().fetchStatus();

    if (!running || !calib.startedAt) {
      setTickElapsed(calib.elapsedSeconds);
      return undefined;
    }
    const tick = () => {
      setTickElapsed(Math.max(0, Date.now() / 1000 - calib.startedAt));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [running, calib.startedAt, calib.elapsedSeconds]);

  const tradePct = calib.tradeBudget > 0 ? Math.min(100, (calib.settledTotal / calib.tradeBudget) * 100) : 0;
  const timePct = calib.timeBudgetSeconds > 0 ? Math.min(100, (tickElapsed / calib.timeBudgetSeconds) * 100) : 0;
  const wr = calib.settledTotal > 0
    ? Math.round((calib.settledWins / calib.settledTotal) * 1000) / 10
    : 0;

  const runStart = async () => {
    setBusy(true);
    try {
      const res = await startCalibration({
        duration_minutes: durationMinutes,
        target_trades: targetTrades,
        autonomy_tier: useSettingsStore.getState().autoGhostCalibrationAutonomyTier,
      });
      if (res?.calibration) useCalibrationStore.getState().applyStatus(res.calibration);
      useToastStore.getState().addToast({
        type: 'info',
        message: 'Calibration started — ghost trades are silent. Your protocol is snapshotted.',
        duration: 5000,
      });
    } catch (err) {
      useToastStore.getState().addToast({
        type: 'error',
        message: `Calibration start failed: ${err.message}`,
      });
    } finally {
      setBusy(false);
      setConfirm(null);
    }
  };

  const runStop = async () => {
    setBusy(true);
    try {
      const res = await stopCalibration();
      if (res?.calibration) useCalibrationStore.getState().applyStatus(res.calibration);
      useToastStore.getState().addToast({
        type: 'info',
        message: 'Calibration stopping — draining in-flight trades, then restoring your protocol.',
        duration: 5000,
      });
    } catch (err) {
      useToastStore.getState().addToast({
        type: 'error',
        message: `Calibration stop failed: ${err.message}`,
      });
    } finally {
      setBusy(false);
      setConfirm(null);
    }
  };

  return (
    <div className="mb-4 rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-3 space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <Activity size={12} className={locked ? 'text-cyan-400 animate-pulse' : 'text-gray-500'} />
          <span className="text-[9.5px] font-black uppercase tracking-widest text-cyan-300">
            {getCalibrationStateLabel(running, draining, calib.state)}
          </span>
        </div>
        {locked && (
          <span 
            title="Simulated trades run invisibly — your live Ghost Protocol is untouched."
            className="text-[8.5px] font-black uppercase tracking-widest text-cyan-200 bg-cyan-500/20 border border-cyan-400/30 rounded px-1.5 py-0.5 cursor-help"
          >
            Silent ⓘ
          </span>
        )}
      </div>

      {locked && (
        <>
          <div className="grid grid-cols-2 gap-2">
            <Meter label={`Trades ${calib.settledTotal}/${calib.tradeBudget}`} pct={tradePct} />
            <Meter label={`Time ${formatClock(tickElapsed)}/${formatClock(calib.timeBudgetSeconds)}`} pct={timePct} />
          </div>
          <div className="flex justify-between text-[8.5px] font-black uppercase tracking-wider text-gray-400">
            <span>WR {calib.settledTotal ? `${wr}%` : '—'}</span>
            <span>PnL {calib.calibrationPnl >= 0 ? '+' : ''}{calib.calibrationPnl.toFixed(2)}</span>
            <span>Budget Progress {Math.round(tradePct)}%</span>
          </div>
          <p className="text-[8.5px] text-cyan-200/80 leading-snug">
            Backend preset is live. Your saved protocol is restored when this ends. Gate sliders are locked.
          </p>
        </>
      )}

      {!locked && (
        <div className="grid grid-cols-2 gap-2">
          <label className="text-[8px] font-black uppercase tracking-wider text-gray-500">
            Minutes
            <input
              type="number"
              min={1}
              max={240}
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Number(e.target.value))}
              className="mt-0.5 h-7 w-full rounded bg-[#25282f] px-2 text-[10px] font-black text-white outline-none border border-white/5"
            />
          </label>
          <label className="text-[8px] font-black uppercase tracking-wider text-gray-500">
            Trade budget
            <input
              type="number"
              min={4}
              max={200}
              value={targetTrades}
              onChange={(e) => setTargetTrades(Number(e.target.value))}
              className="mt-0.5 h-7 w-full rounded bg-[#25282f] px-2 text-[10px] font-black text-white outline-none border border-white/5"
            />
          </label>
        </div>
      )}

      {confirm && (
        <div className="rounded-lg border border-[#ffb800]/40 bg-[#1a1c22] p-2 space-y-2">
          <p className="text-[9px] text-white font-semibold leading-snug">{confirm.text}</p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={confirm.onYes}
              className="flex-1 h-7 rounded bg-[#ffb800] text-black text-[8px] font-black uppercase tracking-widest"
            >
              Confirm
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => setConfirm(null)}
              className="flex-1 h-7 rounded border border-white/10 text-gray-300 text-[8px] font-black uppercase tracking-widest"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {!confirm && (
        <div className="flex gap-2">
          {!locked && (
            <button
              type="button"
              disabled={busy}
              onClick={() => setConfirm({
                text: `Start silent calibration for up to ${targetTrades} trades / ${durationMinutes} min? Your current Ghost protocol is snapshotted and restored when it ends.`,
                onYes: runStart,
              })}
              className="flex-1 h-8 rounded bg-cyan-500/20 border border-cyan-400/40 text-cyan-200 text-[9px] font-black uppercase tracking-widest flex items-center justify-center gap-1"
            >
              <Play size={11} /> Start
            </button>
          )}
          {running && (
            <button
              type="button"
              disabled={busy}
              onClick={() => setConfirm({
                text: 'Stop calibration early? In-flight ghost trades will settle silently, then your protocol is restored.',
                onYes: runStop,
              })}
              className="flex-1 h-8 rounded bg-rose-500/20 border border-rose-400/40 text-rose-200 text-[9px] font-black uppercase tracking-widest flex items-center justify-center gap-1"
            >
              <Square size={11} /> Stop
            </button>
          )}
          {draining && (
            <div className="flex-1 h-8 rounded bg-white/5 border border-white/10 text-gray-400 text-[9px] font-black uppercase tracking-widest flex items-center justify-center">
              Draining…
            </div>
          )}
        </div>
      )}

      {!locked && calib.calibratedGates && (
        <CalibratedGatesCard payload={calib.calibratedGates} />
      )}

      {!locked && calib.strictnessPresets && (
        <div className="space-y-1.5 pt-1 border-t border-white/5">
          <div className="text-[8px] font-black uppercase tracking-widest text-gray-500">
            Backup presets
          </div>
          <div className="grid grid-cols-3 gap-1.5">
            {['relaxed', 'conservative', 'strict'].map((key) => {
              const preset = calib.strictnessPresets[key];
              if (!preset) return null;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    useSettingsStore.getState().mergeGhostProtocols({ [key]: preset });
                    useSettingsStore.getState().loadGhostProtocol(key);
                    useToastStore.getState().addToast({
                      type: 'info',
                      message: `Applied ${preset.name || key} Ghost Protocol.`,
                      duration: 3000,
                    });
                  }}
                  className="h-7 rounded border border-[#ffb800]/30 bg-[#ffb800]/10 text-[#ffb800] text-[8px] font-black uppercase tracking-widest"
                  title={preset.rationale || ''}
                >
                  {preset.name || key}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function CalibratedGatesCard({ payload }) {
  const families = payload?.families || {};
  const bayesian = payload?.bayesian || { ready: false, gates: null };
  const evidence = payload?.evidence;

  // Families default ON if available; Bayesian defaults to FALSE so user can execute without Bayesian filter!
  const [sel, setSel] = useState(() => ({
    zscore: Boolean(families.zscore),
    volatility: Boolean(families.volatility),
    liquidity: Boolean(families.liquidity),
    regimes: Boolean(families.regimes),
    confidence: Boolean(families.confidence),
    manipulation: Boolean(families.manipulation),
    assets: Boolean(families.assets && families.assets.recommended_blacklist?.length > 0),
    bayesian: false,
  }));

  const toggle = (key) => setSel((s) => ({ ...s, [key]: !s[key] }));

  const composeGates = () => {
    const gates = {};
    const push = (fam) => {
      const f = families[fam];
      if (f?.gates) Object.assign(gates, f.gates);
    };
    if (sel.zscore) push('zscore');
    if (sel.volatility) push('volatility');
    if (sel.liquidity) push('liquidity');
    if (sel.regimes) push('regimes');
    if (sel.confidence) push('confidence');
    if (sel.manipulation) push('manipulation');
    if (sel.assets) push('assets');
    if (sel.bayesian) {
      gates.autoGhostBayesianFilterEnabled = true;
      if (bayesian.gates?.autoGhostBayesianMinProbability != null) {
        gates.autoGhostBayesianMinProbability = bayesian.gates.autoGhostBayesianMinProbability;
      }
    } else {
      // Explicitly disable Bayesian filter so calibrated execution runs unhindered
      gates.autoGhostBayesianFilterEnabled = false;
    }
    return gates;
  };

  const handleApply = async () => {
    const gates = composeGates();
    if (Object.keys(gates).length === 0) return;
    useSettingsStore.getState().applyGhostProtocolGates(gates, 'calibrated');
    try {
      const state = useSettingsStore.getState();
      await updateRuntimeStrategyConfig({
        auto_ghost_bayesian_filter_enabled: state.autoGhostBayesianFilterEnabled,
        auto_ghost_bayesian_min_probability: state.autoGhostBayesianMinProbability / 100.0,
        auto_ghost_blacklist_assets: state.ghostBlacklist,
        auto_ghost_min_zscore: state.ghostMinZScoreEnabled ? state.ghostMinZScore : null,
        auto_ghost_min_zscore_enabled: state.ghostMinZScoreEnabled,
        auto_ghost_max_zscore: state.ghostMaxZScoreEnabled ? state.ghostMaxZScore : null,
        auto_ghost_max_zscore_enabled: state.ghostMaxZScoreEnabled,
        auto_ghost_min_confidence: state.ghostMinConfidenceEnabled ? state.ghostMinConfidence : null,
        auto_ghost_min_confidence_enabled: state.ghostMinConfidenceEnabled,
        auto_ghost_max_confidence: state.ghostMaxConfidenceEnabled ? state.ghostMaxConfidence : null,
        auto_ghost_max_confidence_enabled: state.ghostMaxConfidenceEnabled,
        auto_ghost_volatility_gate_enabled: state.autoGhostVolatilityGateEnabled,
        auto_ghost_min_volatility: state.minVolatilityScore,
        auto_ghost_max_volatility: state.maxVolatilityScore,
        auto_ghost_liquidity_gate_enabled: state.autoGhostLiquidityGateEnabled,
        auto_ghost_min_liquidity: state.minLiquidityScore,
        auto_ghost_max_liquidity: state.maxLiquidityScore,
        auto_ghost_regime_gate_enabled: state.ghostRegimeGateEnabled,
        auto_ghost_allowed_regimes: state.ghostAllowedRegimes,
        auto_ghost_require_regime_stable: state.ghostRequireRegimeStable,
        auto_ghost_manipulation_severity_threshold: state.autoGhostManipulationSeverityThreshold,
        auto_ghost_block_on_manipulation: state.autoGhostBlockOnManipulation,
      });
    } catch (err) {
      console.warn('[CalibrationPanel] Immediate runtime sync failed:', err);
    }
    useToastStore.getState().addToast({
      type: 'info',
      message: 'Calibrated gates applied to your Ghost Protocol.',
      duration: 3000,
    });
  };

  const handleSave = () => {
    const gates = composeGates();
    if (Object.keys(gates).length === 0) return;
    const name = `Calibrated ${new Date().toISOString().slice(0, 10)}`;
    useSettingsStore.getState().mergeGhostProtocols({ calibrated: { name, gates } });
    useToastStore.getState().addToast({
      type: 'info',
      message: `Saved "${name}" to your Ghost Protocols.`,
      duration: 3000,
    });
  };

  const primeAssets = payload?.prime_assets || families.assets?.prime_assets || [];
  const hazardAssets = payload?.recommended_blacklist || families.assets?.recommended_blacklist || [];

  const anySelected = Object.values(sel).some(Boolean);
  const option = (key, label, enabled, title, extraClass = '') => (
    <button
      key={key}
      type="button"
      disabled={!enabled}
      onClick={() => toggle(key)}
      title={title || ''}
      className={`h-6 rounded border text-[8.5px] font-black uppercase tracking-wider px-1.5 transition-colors flex items-center justify-center ${extraClass} ${
        !enabled
          ? 'border-white/5 bg-white/5 text-gray-600 cursor-not-allowed'
          : sel[key]
            ? 'border-cyan-400/40 bg-cyan-500/15 text-cyan-200'
            : 'border-white/10 bg-white/5 text-gray-400 hover:text-white hover:border-white/20'
      }`}
    >
      {sel[key] && enabled ? '✓ ' : ''}{label}
    </button>
  );

  return (
    <div className="space-y-2 pt-1 border-t border-amber-500/20">
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-black uppercase tracking-widest text-amber-300">
          Apply Calibrated Gates
        </span>
        {evidence && (
          <span className="text-[8px] font-bold text-gray-400">
            N={evidence.settled} · WR {evidence.win_rate ?? '—'}%
          </span>
        )}
      </div>

      <div className="grid grid-cols-4 gap-1.5">
        {option('zscore', 'Z-Score', Boolean(families.zscore), families.zscore?.rationale)}
        {option('volatility', 'Volatility', Boolean(families.volatility), families.volatility?.rationale)}
        {option('liquidity', 'Liquidity', Boolean(families.liquidity), families.liquidity?.rationale)}
        {option('confidence', 'Confidence', Boolean(families.confidence), families.confidence?.rationale)}
        {option('manipulation', 'Manip', Boolean(families.manipulation), families.manipulation?.rationale)}
        {option('regimes', 'Regimes', Boolean(families.regimes), families.regimes?.rationale)}
        {option(
          'assets',
          `Blacklist (${hazardAssets.length})`,
          hazardAssets.length > 0,
          families.assets?.rationale || (hazardAssets.length > 0 ? `Blacklist ${hazardAssets.join(', ')}` : 'No toxic assets flagged in this session.'),
          'col-span-2'
        )}
      </div>

      {/* Asset Performance Profiling (Prime vs Hazard) */}
      {(primeAssets.length > 0 || hazardAssets.length > 0) && (
        <div className="rounded-lg bg-black/40 border border-white/5 p-2 space-y-1 text-[8.5px]">
          <div className="flex items-center justify-between text-[7.5px] font-black uppercase tracking-wider text-gray-500 font-sans">
            <span>Asset Performance Profiling</span>
            <span className="text-[7px] text-gray-400">Calibration Run</span>
          </div>
          <div className="flex flex-wrap gap-1 pt-0.5">
            {primeAssets.map((asset) => (
              <span
                key={asset}
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 font-mono text-[8px]"
                title="Prime Asset: High win rate and low manipulation during calibration"
              >
                ★ {asset.replace('_otc', '')} <span className="text-[7px] text-emerald-400/70 font-sans font-bold">PRIME</span>
              </span>
            ))}
            {hazardAssets.map((asset) => (
              <span
                key={asset}
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300 font-mono text-[8px]"
                title="Hazard Asset: High loss rate or severe manipulation during calibration"
              >
                🚩 {asset.replace('_otc', '')} <span className="text-[7px] text-rose-400/70 font-sans font-bold">HAZARD</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Bayesian Option Row */}
      <div className="pt-0.5">
        {option(
          'bayesian',
          `Bayesian Filter ${bayesian.ready ? '(Ready)' : '(Not Ready 🔒)'}`,
          Boolean(bayesian.ready),
          bayesian.ready
            ? 'Prior store READY (N>=500). Enables Bayesian probability floor filter.'
            : 'Prior store NOT READY (N<500) — keep unchecked to execute on protocol gates without Bayesian blocking.',
        )}
      </div>

      {/* Live Gate Values Preview */}
      <div className="rounded-lg bg-black/40 border border-white/5 p-2 space-y-1 font-mono text-[8.5px]">
        <div className="text-[7.5px] font-black tracking-wider text-gray-500 uppercase font-sans">
          Preview of Gates to Apply
        </div>
        <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-gray-300">
          {sel.zscore && families.zscore?.gates && (
            <div>• Z-Score: <span className="text-cyan-300">[{families.zscore.gates.ghostMinZScore}, {families.zscore.gates.ghostMaxZScore}]</span></div>
          )}
          {sel.volatility && families.volatility?.gates && (
            <div>• Vol: <span className="text-cyan-300">{families.volatility.gates.minVolatilityScore}%–{families.volatility.gates.maxVolatilityScore}%</span></div>
          )}
          {sel.liquidity && families.liquidity?.gates && (
            <div>• Liq: <span className="text-cyan-300">{families.liquidity.gates.minLiquidityScore}%–{families.liquidity.gates.maxLiquidityScore}%</span></div>
          )}
          {sel.confidence && families.confidence?.gates && (
            <div>• Conf: <span className="text-cyan-300">≥{families.confidence.gates.ghostMinConfidence}%</span></div>
          )}
          {sel.manipulation && families.manipulation?.gates && (
            <div>• Manip: <span className="text-cyan-300">≤{families.manipulation.gates.autoGhostManipulationSeverityThreshold}</span></div>
          )}
          {sel.regimes && families.regimes?.gates && (
            <div className="col-span-2 truncate">• Regimes: <span className="text-cyan-300">{(families.regimes.gates.ghostAllowedRegimes || []).join(', ') || 'All'}</span></div>
          )}
          {sel.assets && hazardAssets.length > 0 && (
            <div className="col-span-2 truncate">
              • Suspend: <span className="text-rose-400 font-mono">{hazardAssets.map(a => a.replace('_otc', '')).join(', ')}</span>
            </div>
          )}
          {sel.bayesian && bayesian.gates && (
            <div>• Bayesian: <span className="text-amber-300">≥{bayesian.gates.autoGhostBayesianMinProbability}%</span></div>
          )}
          {!sel.bayesian && (
            <div>• Bayesian: <span className="text-gray-500">Disabled (Bypassed)</span></div>
          )}
        </div>
      </div>

      <div className="flex gap-1.5 pt-0.5">
        <button
          type="button"
          disabled={!anySelected}
          onClick={handleApply}
          className="flex-1 h-7 rounded bg-amber-400 hover:bg-amber-300 text-black text-[9px] font-black uppercase tracking-widest disabled:opacity-40 transition-colors shadow-sm"
        >
          ⚡ Apply Calibrated Gates
        </button>
        <button
          type="button"
          disabled={!anySelected}
          onClick={handleSave}
          className="flex-1 h-7 rounded border border-amber-400/40 bg-amber-400/10 hover:bg-amber-400/20 text-amber-300 text-[9px] font-black uppercase tracking-widest disabled:opacity-40 transition-colors"
        >
          Save as Protocol
        </button>
      </div>
      {families.regimes?.proposal && (
        <div className="text-[7.5px] text-gray-500 leading-tight">
          Regimes from Guardian proposal (N={families.regimes.evidence_n}): {families.regimes.rationale}
        </div>
      )}
    </div>
  );
}

function Meter({ label, pct }) {
  return (
    <div>
      <div className="text-[8px] font-black uppercase tracking-wider text-gray-400 mb-0.5 truncate">{label}</div>
      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <div className="h-full bg-cyan-400 transition-all duration-300" style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
      </div>
    </div>
  );
}
