import { useEffect, useState } from 'react';
import { Activity, Square, Play } from 'lucide-react';
import { useCalibrationStore, isCalibrationLockedState } from '../../stores/useCalibrationStore.js';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useToastStore } from '../../stores/useToastStore.js';
import { startCalibration, stopCalibration } from '../../api/strategyApi.js';

function formatClock(totalSec) {
  const sec = Math.max(0, Math.round(Number(totalSec) || 0));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
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
          <span className="text-[9px] font-black uppercase tracking-widest text-cyan-300">
            {running ? 'Calibrating' : draining ? `Draining (${calib.state})` : calib.state === 'DONE' ? 'Calibration Done' : calib.state === 'ABORTED' ? 'Calibration Aborted' : 'Calibration Mode'}
          </span>
        </div>
        {locked && (
          <span className="text-[8px] font-black uppercase tracking-widest text-cyan-200 bg-cyan-500/20 border border-cyan-400/30 rounded px-1.5 py-0.5">
            Silent
          </span>
        )}
      </div>

      {locked && (
        <>
          <div className="grid grid-cols-2 gap-2">
            <Meter label={`Trades ${calib.settledTotal}/${calib.tradeBudget}`} pct={tradePct} />
            <Meter label={`Time ${formatClock(tickElapsed)}/${formatClock(calib.timeBudgetSeconds)}`} pct={timePct} />
          </div>
          <div className="flex justify-between text-[8px] font-black uppercase tracking-wider text-gray-400">
            <span>WR {calib.settledTotal ? `${wr}%` : '—'}</span>
            <span>PnL {calib.calibrationPnl >= 0 ? '+' : ''}{calib.calibrationPnl.toFixed(2)}</span>
            <span>Sufficiency {Math.round(tradePct)}%</span>
          </div>
          <p className="text-[8px] text-cyan-200/80 leading-snug">
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

      {!locked && calib.strictnessPresets && (
        <div className="space-y-1.5 pt-1 border-t border-white/5">
          <div className="text-[8px] font-black uppercase tracking-widest text-gray-500">
            Apply calibrated profile
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

function Meter({ label, pct }) {
  return (
    <div>
      <div className="text-[7px] font-black uppercase tracking-wider text-gray-500 mb-0.5 truncate">{label}</div>
      <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div className="h-full bg-cyan-400" style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
      </div>
    </div>
  );
}
