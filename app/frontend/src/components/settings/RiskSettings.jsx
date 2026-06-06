/**
 * RiskSettings — capital, payout, sizing, drawdown, and trade-run controls.
 * Redesigned to follow the Stitch Design Reference.
 */
import { useMemo } from 'react';
import { 
  Calculator, CircleDollarSign, Layers3, Target, Trophy, Wallet,
  Activity, RefreshCcw
} from 'lucide-react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { computeRiskMetrics } from '../../utils/riskMath.js';
import { SectionCard, InputGroup, NumberInput, StitchToggle } from '../shared/StitchComponents.jsx';

function MetricTile({ label, value, note, icon: Icon }) {
  return (
    <div className="rounded-xl border border-white/5 bg-[#25282f]/30 p-5 transition hover:border-white/10">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-black uppercase tracking-widest text-gray-500">{label}</p>
          <p className="mt-2 text-xl font-black text-white">{value}</p>
          <p className="mt-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-600 leading-normal">{note}</p>
        </div>
        {Icon && (
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#25282f] text-[#ffb800]">
            <Icon size={18} />
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
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <div className="space-y-6">
        <SectionCard 
          title="Session Capital" 
          subtitle="Configure base values and trade sizing parameters." 
          icon={Wallet}
        >
          <div className="grid gap-6 md:grid-cols-2">
            <InputGroup 
              label="Initial Balance" 
              description="Base funding for drawdown calculations."
            >
              <NumberInput
                value={initialBalance}
                onChange={setInitialBalance}
                min={0}
                suffix="USD"
                icon={Wallet}
              />
            </InputGroup>

            <InputGroup 
              label="Payout Percentage" 
              description="Expected payout rate for the asset class."
            >
              <NumberInput
                value={payoutPercentage}
                onChange={setPayoutPercentage}
                min={0}
                suffix="%"
                icon={Activity}
              />
            </InputGroup>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <InputGroup 
              label="Risk % Per Trade" 
              description="Proportional stake sizing per entry."
            >
              <NumberInput
                value={riskPercentPerTrade}
                onChange={setRiskPercentPerTrade}
                min={0}
                suffix="%"
                icon={Target}
              />
            </InputGroup>

            <InputGroup 
              label="Drawdown Max" 
              description="Tolerated loss percentage before session halt."
            >
              <NumberInput
                value={drawdownPercent}
                onChange={setDrawdownPercent}
                min={0}
                suffix="%"
                icon={RefreshCcw}
              />
            </InputGroup>
          </div>
        </SectionCard>

        <SectionCard 
          title="Execution Sizing & Bounds" 
          subtitle="Choose sizing mode and configure trade cycle targets." 
          icon={CircleDollarSign}
        >
          <div className="rounded-xl border border-white/5 bg-[#25282f]/20 p-5">
            <InputGroup 
              label="Fixed Sizing Mode" 
              description="Override relative percentage sizing with a constant dollar stake."
              layout="horizontal"
            >
              <StitchToggle
                checked={useFixedAmount}
                onChange={setUseFixedAmount}
              />
            </InputGroup>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <InputGroup 
              label="Fixed Risk Amount" 
              description="Stake size applied when fixed mode is active."
            >
              <NumberInput
                value={fixedRiskAmount}
                onChange={setFixedRiskAmount}
                min={0}
                suffix="USD"
                icon={Wallet}
              />
            </InputGroup>

            <InputGroup 
              label="Risk Reward Ratio" 
              description="Take profit margin relative to risk distance."
            >
              <NumberInput
                value={riskRewardRatio}
                onChange={setRiskRewardRatio}
                min={0}
                suffix="Ratio"
                icon={Target}
              />
            </InputGroup>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <InputGroup 
              label="Trades Per Run" 
              description="Entries comprising a single trade lifecycle."
            >
              <NumberInput
                value={tradesPerRun}
                onChange={setTradesPerRun}
                min={1}
                suffix="Trades"
                icon={Activity}
              />
            </InputGroup>

            <InputGroup 
              label="Max Runs Per Session" 
              description="Upper session limit on consecutive lifecycles."
            >
              <NumberInput
                value={maxRuns}
                onChange={setMaxRuns}
                min={1}
                suffix="Runs"
                icon={RefreshCcw}
              />
            </InputGroup>
          </div>
        </SectionCard>
      </div>

      <div className="space-y-6">
        <SectionCard 
          title="Risk Telemetry Preview" 
          subtitle="Dynamic computations based on current sizing coefficients." 
          icon={Calculator}
        >
          <div className="grid gap-4 md:grid-cols-2">
            <MetricTile
              label="Risk per Trade"
              value={`$${metrics.riskPerTrade.toFixed(2)}`}
              note={useFixedAmount ? 'Using absolute fixed staking.' : `Proportional sizing @ ${Number(riskPercentPerTrade).toFixed(2)}% of balance.`}
              icon={Trophy}
            />
            <MetricTile
              label="Drawdown Threshold"
              value={`$${metrics.maxDrawdownLimit.toFixed(2)}`}
              note={`Termination boundary at ${Number(drawdownPercent).toFixed(2)}% drawdown.`}
              icon={Layers3}
            />
            <MetricTile
              label="Target Take Profit"
              value={`$${metrics.takeProfitTarget.toFixed(2)}`}
              note={`Calculated profit trigger based on ${Number(riskRewardRatio).toFixed(2)} ratio.`}
              icon={Target}
            />
            <MetricTile
              label="Stat Minimum Win Rate"
              value={`${metrics.minimumWinRate.toFixed(1)}%`}
              note="Calculated baseline break-even rate based on broker payout."
              icon={Wallet}
            />
          </div>

          <div className="rounded-xl border border-white/5 bg-[#25282f]/20 p-5 text-xs font-medium uppercase tracking-normal leading-relaxed text-gray-500">
            The mathematical engine synchronizes values in real-time. Input boundaries are evaluated automatically prior to store persistence.
          </div>
        </SectionCard>
      </div>
    </div>
  );
}