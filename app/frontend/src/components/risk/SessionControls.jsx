import { ArrowRightLeft, PlayCircle, RotateCcw, Download, StopCircle, Plus } from 'lucide-react';

export default function SessionControls({
  recordingMode,
  onModeChange,
  onAddTrade,
  onNewRun,
  onSync,
  onExport,
  onReset,
  canAddTrades,
}) {
  const isAuto = recordingMode === 'auto';

  return (
    <div className="rounded-2xl border border-white/5 bg-[#0f1419] p-4 shadow-[0_10px_30px_rgba(0,0,0,0.22)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.26em] text-gray-500">Session Controls</p>
          <p className="mt-1 text-sm font-semibold text-[#e3e6e7]">Auto recording, manual entry, and override tools</p>
        </div>

        <div className="inline-flex rounded-xl border border-white/5 bg-[#10151a] p-1">
          <ModeButton active={isAuto} onClick={() => onModeChange('auto')} icon={PlayCircle} label="Auto" />
          <ModeButton active={!isAuto} onClick={() => onModeChange('manual')} icon={ArrowRightLeft} label="Manual" />
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <ActionButton
          label="Add Win"
          icon={PlayCircle}
          tone="emerald"
          disabled={!canAddTrades || isAuto}
          onClick={() => onAddTrade('win')}
        />
        <ActionButton
          label="Add Loss"
          icon={StopCircle}
          tone="rose"
          disabled={!canAddTrades || isAuto}
          onClick={() => onAddTrade('loss')}
        />
        <ActionButton
          label="Add Void"
          icon={Plus}
          tone="slate"
          disabled={!canAddTrades || isAuto}
          onClick={() => onAddTrade('void')}
        />
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <UtilityButton label="New Trade Run" icon={Plus} onClick={onNewRun} />
        <UtilityButton label="Sync" icon={ArrowRightLeft} onClick={onSync} />
        <UtilityButton label="Export" icon={Download} onClick={onExport} />
        <UtilityButton label="Reset" icon={RotateCcw} onClick={onReset} />
      </div>

      {isAuto && (
        <p className="mt-3 text-[11px] text-gray-500">
          Auto mode records WIN / LOSS / VOID from real SSID trade results. Switch to Manual for direct entries.
        </p>
      )}
    </div>
  );
}

function ModeButton({ active, onClick, icon: Icon, label }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] transition ${active ? 'bg-[#f5df19] text-black shadow-sm' : 'text-gray-500 hover:text-[#e3e6e7]'}`}
    >
      <Icon size={13} />
      {label}
    </button>
  );
}

function ActionButton({ label, icon: Icon, tone, disabled, onClick }) {
  const toneClasses = {
    emerald: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-400 hover:bg-emerald-400/15',
    rose: 'border-red-400/20 bg-red-400/10 text-red-400 hover:bg-red-400/15',
    slate: 'border-white/5 bg-white/5 text-[#e3e6e7] hover:bg-white/10',
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center justify-center gap-2 rounded-xl border px-4 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-45 ${toneClasses[tone]}`}
    >
      <Icon size={15} />
      {label}
    </button>
  );
}

function UtilityButton({ label, icon: Icon, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center justify-center gap-2 rounded-xl border border-white/5 bg-[#10151a] px-3 py-2.5 text-xs font-semibold uppercase tracking-[0.16em] text-[#e3e6e7] transition hover:bg-[#171d24]"
    >
      <Icon size={13} />
      {label}
    </button>
  );
}