/**
 * RiskSettings — capital, payout, sizing, drawdown, and trade-run controls.
 */
import { useMemo } from 'react';
import { Calculator, CircleDollarSign, Layers3, Target, Trophy, Wallet } from 'lucide-react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { computeRiskMetrics } from '../../utils/riskMath.js';

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

function MetricTile({ label, value, note, icon: Icon }) {
  return (
    <div className="rounded-2xl border border-white/5 bg-[#0f1419] px-4 py-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">{label}</p>
          <p className="mt-1 text-xl font-black tracking-tight text-[#e3e6e7]">{value}</p>
          <p className="mt-1 text-xs text-gray-500">{note}</p>
        </div>
        {Icon && (
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#151a22] text-[#f5df19]">
            <Icon size={16} />
          </div>
        )}
      </div>
    </div>
  );
}

export default function RiskSettings() {
  const {
    initialBalance,
    payoutPercentage,
    riskPercentPerTrade,
    drawdownPercent,
    riskRewardRatio,
    useFixedAmount,
    fixedRiskAmount,
    tradesPerRun,
    maxRuns,
    setInitialBalance,
    setPayoutPercentage,
    setRiskPercentPerTrade,
    setDrawdownPercent,
    setRiskRewardRatio,
    setUseFixedAmount,
    setFixedRiskAmount,
    setTradesPerRun,
    setMaxRuns,
  } = useSettingsStore();

  const metrics = useMemo(() => computeRiskMetrics({
    startBalance: initialBalance,
    payoutPercentage,
    riskPercentPerTrade,
    drawdownPercent,
    riskRewardRatio,
    useFixedAmount,
    fixedRiskAmount,
    currentSessionPnl: 0,
  }), [
    initialBalance,
    payoutPercentage,
    riskPercentPerTrade,
    drawdownPercent,
    riskRewardRatio,
    useFixedAmount,
    fixedRiskAmount,
  ]);

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <SectionCard title="Session capital" subtitle="Configure the balance and trade-sizing assumptions for the current session." icon={Wallet}>
        <div className="grid gap-3 md:grid-cols-2">
          <NumberField
            label="Initial balance"
            description="Starting session balance used by risk math and drawdown calculations."
            value={initialBalance}
            onChange={setInitialBalance}
            min={0}
            step={0.01}
            suffix="balance"
          />
          <NumberField
            label="Payout percentage"
            description="Expected payout percentage for the selected broker / asset class."
            value={payoutPercentage}
            onChange={setPayoutPercentage}
            min={0}
            step={0.1}
            suffix="payout"
          />
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <NumberField
            label="Risk % per trade"
            description="Percentage of the starting balance risked on each trade when fixed amount is off."
            value={riskPercentPerTrade}
            onChange={setRiskPercentPerTrade}
            min={0}
            step={0.1}
            suffix="risk"
          />
          <NumberField
            label="Drawdown %"
            description="Maximum tolerated drawdown before the session is considered at limit."
            value={drawdownPercent}
            onChange={setDrawdownPercent}
            min={0}
            step={0.1}
            suffix="dd"
          />
        </div>
      </SectionCard>

      <SectionCard title="Sizing mode" subtitle="Choose between percentage sizing and a fixed risk amount per trade." icon={CircleDollarSign}>
        <ToggleRow
          label="Use fixed amount"
          description="Override percentage sizing and use the fixed dollar amount below."
          checked={useFixedAmount}
          onChange={setUseFixedAmount}
        />
        <NumberField
          label="Fixed risk amount"
          description="Amount risked per trade when fixed amount mode is enabled."
          value={fixedRiskAmount}
          onChange={setFixedRiskAmount}
          min={0}
          step={0.1}
          suffix="risk"
        />
        <div className="grid gap-3 md:grid-cols-2">
          <NumberField
            label="Risk:reward ratio"
            description="Take-profit distance relative to drawdown distance."
            value={riskRewardRatio}
            onChange={setRiskRewardRatio}
            min={0}
            step={0.1}
            suffix="ratio"
          />
          <NumberField
            label="Trades per run"
            description="How many trades make up a single focused Trade Run."
            value={tradesPerRun}
            onChange={setTradesPerRun}
            min={1}
            step={1}
            suffix="run"
          />
        </div>
        <NumberField
          label="Max runs per session"
          description="Hard limit on the number of Trade Runs in one session."
          value={maxRuns}
          onChange={setMaxRuns}
          min={1}
          step={1}
          suffix="runs"
        />
      </SectionCard>

      <SectionCard title="Risk preview" subtitle="Derived values update immediately as you edit the settings." icon={Calculator}>
        <div className="grid gap-3 md:grid-cols-2">
          <MetricTile
            label="Risk / trade"
            value={`$${metrics.riskPerTrade.toFixed(2)}`}
            note={useFixedAmount ? 'Using fixed amount mode.' : `Based on ${Number(riskPercentPerTrade).toFixed(2)}% of start balance.`}
            icon={Trophy}
          />
          <MetricTile
            label="Drawdown cap"
            value={`$${metrics.maxDrawdownLimit.toFixed(2)}`}
            note={`Hard stop at ${Number(drawdownPercent).toFixed(2)}% drawdown.`}
            icon={Layers3}
          />
          <MetricTile
            label="Take-profit target"
            value={`$${metrics.takeProfitTarget.toFixed(2)}`}
            note={`Computed from risk:reward ratio ${Number(riskRewardRatio).toFixed(2)}.`}
            icon={Target}
          />
          <MetricTile
            label="Min win rate"
            value={`${metrics.minimumWinRate.toFixed(1)}%`}
            note="Reference benchmark derived from broker payout."
            icon={Wallet}
          />
        </div>

        <div className="rounded-2xl border border-white/5 bg-[#0f1419] px-4 py-4 text-xs leading-6 text-gray-400">
          The risk manager reads these settings directly. Inputs are sanitized before persistence so the session math never receives invalid ranges.
        </div>
      </SectionCard>
    </div>
  );
}