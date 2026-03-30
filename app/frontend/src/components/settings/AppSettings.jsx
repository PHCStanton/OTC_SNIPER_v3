/**
 * AppSettings — OTEO, ghost trading, trading controls, and UI preferences.
 */
import { Circle, Eye, Gauge, Ghost, LayoutGrid, MessageSquareWarning, SlidersHorizontal, Target, Bot } from 'lucide-react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';

function SectionCard({ title, subtitle, icon: Icon, children }) {
  return (
    <section className="rounded-3xl border border-white/5 bg-[#151a22]/95 p-5 shadow-[0_15px_40px_rgba(0,0,0,0.28)]">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-bold tracking-tight text-[#e3e6e7]">{title}</h3>
          <p className="mt-1 text-xs text-gray-500">{subtitle}</p>
        </div>
        {Icon && (
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#0f1419] text-[#f5df19]">
            <Icon size={18} />
          </div>
        )}
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function ToggleRow({ label, description, checked, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex w-full items-center justify-between gap-4 rounded-2xl border border-white/5 bg-[#0f1419] px-4 py-4 text-left transition-colors hover:bg-white/5"
    >
      <div>
        <p className="text-sm font-bold text-[#e3e6e7]">{label}</p>
        <p className="mt-1 text-xs leading-5 text-gray-500">{description}</p>
      </div>
      <span className={`relative inline-flex h-6 w-11 items-center rounded-full p-0.5 transition-colors ${checked ? 'bg-[#f5df19]' : 'bg-white/10'}`}>
        <span className={`h-5 w-5 rounded-full bg-white transition-transform ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
      </span>
    </button>
  );
}

function NumberField({ label, description, value, onChange, min, step = 1, suffix }) {
  return (
    <label className="block rounded-2xl border border-white/5 bg-[#0f1419] px-4 py-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-[#e3e6e7]">{label}</p>
          <p className="mt-1 text-xs leading-5 text-gray-500">{description}</p>
        </div>
        {suffix && <span className="rounded-full border border-white/5 bg-white/5 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-400">{suffix}</span>}
      </div>
      <input
        type="number"
        min={min}
        step={step}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-3 w-full rounded-xl border border-white/10 bg-white px-4 py-3 text-sm font-bold text-black outline-none transition focus:border-[#f5df19] focus:bg-white"
      />
    </label>
  );
}

export default function AppSettings() {
  const {
    oteoEnabled,
    oteoWarmupBars,
    oteoCooldownBars,
    ghostTradingEnabled,
    ghostAmount,
    maxDailyLoss,
    maxTradesPerSession,
    stopOnLossStreak,
    aiModel,
    showManipulationAlerts,
    showSignalConfidence,
    autoFocusOnSignal,
    setOteoEnabled,
    setOteoWarmupBars,
    setOteoCooldownBars,
    setGhostTradingEnabled,
    setGhostAmount,
    setMaxDailyLoss,
    setMaxTradesPerSession,
    setStopOnLossStreak,
    setAiModel,
    setShowManipulationAlerts,
    setShowSignalConfidence,
    setAutoFocusOnSignal,
  } = useSettingsStore();

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <SectionCard title="OTEO" subtitle="Signal warmup and cooldown stay in the app layer, not the session layer." icon={Target}>
        <ToggleRow
          label="Enable OTEO"
          description="Turn signal warmup / cooldown handling on or off for the trading workspace."
          checked={oteoEnabled}
          onChange={setOteoEnabled}
        />
        <div className="grid gap-3 md:grid-cols-2">
          <NumberField
            label="Warmup bars"
            description="Bars required before the signal can be trusted."
            value={oteoWarmupBars}
            onChange={setOteoWarmupBars}
            min={0}
            step={1}
            suffix="bars"
          />
          <NumberField
            label="Cooldown bars"
            description="Bars to wait before the signal can fire again."
            value={oteoCooldownBars}
            onChange={setOteoCooldownBars}
            min={0}
            step={1}
            suffix="bars"
          />
        </div>
      </SectionCard>

      <SectionCard title="Ghost trading" subtitle="Simulation mode for previewing execution without a live trade." icon={Ghost}>
        <ToggleRow
          label="Enable ghost trading"
          description="Use the ghost execution path for dry runs and visual validation."
          checked={ghostTradingEnabled}
          onChange={setGhostTradingEnabled}
        />
        <NumberField
          label="Ghost trade amount"
          description="Simulated amount used when ghost trading is enabled."
          value={ghostAmount}
          onChange={setGhostAmount}
          min={0}
          step={0.1}
          suffix="amount"
        />
      </SectionCard>

      <SectionCard title="Trading controls" subtitle="Session-level guardrails that shape how long the workspace can keep trading." icon={Gauge}>
        <NumberField
          label="Max daily loss"
          description="Soft stop when the session reaches this total loss amount."
          value={maxDailyLoss}
          onChange={setMaxDailyLoss}
          min={0}
          step={0.1}
          suffix="loss cap"
        />
        <NumberField
          label="Max trades per session"
          description="Hard cap on the number of trades that can be executed in one session."
          value={maxTradesPerSession}
          onChange={setMaxTradesPerSession}
          min={1}
          step={1}
          suffix="trades"
        />
        <NumberField
          label="Stop on loss streak"
          description="Stop trading after this many consecutive losses."
          value={stopOnLossStreak}
          onChange={setStopOnLossStreak}
          min={0}
          step={1}
          suffix="streak"
        />
      </SectionCard>

      <SectionCard title="AI integration" subtitle="Choose the default model used by the advisory assistant." icon={Bot}>
        <label className="block rounded-2xl border border-white/5 bg-[#0f1419] px-4 py-4">
          <p className="text-sm font-bold text-[#e3e6e7]">Default AI model</p>
          <p className="mt-1 text-xs leading-5 text-gray-500">Used by the AI tab when no model override is supplied.</p>
          <select
            value={aiModel}
            onChange={(event) => setAiModel(event.target.value)}
            className="mt-3 w-full rounded-xl border border-white/10 bg-white px-4 py-3 text-sm font-bold text-black outline-none transition focus:border-[#f5df19]"
          >
            <option value="grok-4-1-fast-non-reasoning">grok-4-1-fast-non-reasoning</option>
            <option value="grok-4-1-fast-reasoning">grok-4-1-fast-reasoning</option>
            <option value="grok-4">grok-4</option>
          </select>
        </label>
      </SectionCard>

      <SectionCard title="UI preferences" subtitle="Visual and attention settings stay separate from execution logic." icon={LayoutGrid}>
        <ToggleRow
          label="Show manipulation alerts"
          description="Surface manipulation warnings in the workspace when signals are flagged."
          checked={showManipulationAlerts}
          onChange={setShowManipulationAlerts}
        />
        <ToggleRow
          label="Show signal confidence"
          description="Display the confidence ring and signal confidence readouts."
          checked={showSignalConfidence}
          onChange={setShowSignalConfidence}
        />
        <ToggleRow
          label="Auto-focus on signal"
          description="Move attention to the active signal area when a new setup appears."
          checked={autoFocusOnSignal}
          onChange={setAutoFocusOnSignal}
        />

        <div className="rounded-2xl border border-white/5 bg-[#0f1419] px-4 py-4 text-xs leading-6 text-gray-400">
          <div className="flex items-center gap-2 font-semibold text-[#e3e6e7]">
            <MessageSquareWarning size={14} className="text-[#f5df19]" />
            Validation note
          </div>
          <p className="mt-2">
            All setters in useSettingsStore clamp values before persistence so the UI cannot save invalid ranges.
          </p>
        </div>
      </SectionCard>
    </div>
  );
}