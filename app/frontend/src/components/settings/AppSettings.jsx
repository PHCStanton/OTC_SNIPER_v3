/**
 * AppSettings — Global System Settings following the Stitch Design Reference.
 */
import { useState } from 'react';
import {
  Target, Bot, Ghost, Gauge, Volume2, LayoutGrid,
  ChevronDown, Info, ShieldAlert, Activity, Zap,
  BarChart3, Settings2, RefreshCcw, Save
} from 'lucide-react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';

import ghostStatic from '../../../assets/Ghost_Icon.png';
import bobble from '../../../assets/bobble.gif';
import bounce from '../../../assets/bounce.gif';
import cuteHop from '../../../assets/cute-hop.gif';
import dealWithIt from '../../../assets/deal-with-it.gif';
import drift from '../../../assets/drift.gif';
import elastic from '../../../assets/elastic-corner-pinch.gif';
import excited from '../../../assets/excited.gif';
import flagWave from '../../../assets/flag-wave.gif';
import hovering from '../../../assets/hovering.gif';
import party from '../../../assets/party.gif';
import radarPing from '../../../assets/radar-ping.gif';
import scanning from '../../../assets/scanning.gif';
import spin from '../../../assets/spin.gif';
import weird from '../../../assets/weird.gif';
import wobble from '../../../assets/wobble.gif';

const GHOST_OPTIONS = [
  { id: 'drift.gif', name: 'Drifting', src: drift },
  { id: 'Ghost_Icon.png', name: 'Static (Original)', src: ghostStatic },
  { id: 'bobble.gif', name: 'Bobble', src: bobble },
  { id: 'bounce.gif', name: 'Bounce', src: bounce },
  { id: 'cute-hop.gif', name: 'Cute Hop', src: cuteHop },
  { id: 'deal-with-it.gif', name: 'Deal With It', src: dealWithIt },
  { id: 'elastic-corner-pinch.gif', name: 'Elastic', src: elastic },
  { id: 'excited.gif', name: 'Excited', src: excited },
  { id: 'flag-wave.gif', name: 'Flag Wave', src: flagWave },
  { id: 'hovering.gif', name: 'Hovering', src: hovering },
  { id: 'party.gif', name: 'Party', src: party },
  { id: 'radar-ping.gif', name: 'Radar Ping', src: radarPing },
  { id: 'scanning.gif', name: 'Scanning', src: scanning },
  { id: 'spin.gif', name: 'Spin', src: spin },
  { id: 'weird.gif', name: 'Weird', src: weird },
  { id: 'wobble.gif', name: 'Wobble', src: wobble },
];

function SectionCard({ title, subtitle, icon: Icon, children, badge, toggle, onToggle }) {
  return (
    <section className="relative overflow-hidden rounded-[20px] bg-[#1a1c22] p-6 shadow-xl border border-white/5">
      <div className="mb-6 flex items-start justify-between">
        <div className="flex gap-4">
          {Icon && (
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#25282f] text-[#ffb800]">
              <Icon size={24} />
            </div>
          )}
          <div>
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-black uppercase tracking-wider text-white">{title}</h3>
              {badge && (
                <span className="rounded-md bg-[#ffb800]/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-[#ffb800] border border-[#ffb800]/20">
                  {badge}
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-gray-500 font-medium">{subtitle}</p>
          </div>
        </div>
        {toggle !== undefined && (
          <button
            type="button"
            onClick={() => onToggle(!toggle)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none ${
              toggle ? 'bg-[#ffb800]' : 'bg-[#2d3139]'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${
                toggle ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        )}
      </div>
      <div className="space-y-6">{children}</div>
    </section>
  );
}

function InputGroup({ label, description, children, layout = 'vertical' }) {
  return (
    <div className={`flex ${layout === 'horizontal' ? 'flex-row items-center justify-between' : 'flex-col space-y-2'}`}>
      <div className={layout === 'horizontal' ? 'flex-1' : ''}>
        <p className="text-[11px] font-black uppercase tracking-[0.15em] text-gray-400">{label}</p>
        {description && <p className="mt-1 text-[11px] font-medium text-gray-600 leading-relaxed uppercase">{description}</p>}
      </div>
      <div className={layout === 'horizontal' ? 'ml-4' : 'mt-2'}>
        {children}
      </div>
    </div>
  );
}

function NumberInput({ value, onChange, min, suffix, icon: Icon }) {
  return (
    <div className="flex h-14 w-full items-center overflow-hidden rounded-lg bg-white shadow-inner">
      <div className="flex h-full w-12 items-center justify-center bg-gray-50 text-gray-400">
        {Icon ? <Icon size={18} /> : <span className="text-lg font-bold">#</span>}
      </div>
      <input
        type="number"
        min={min}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-full flex-1 px-4 text-xl font-black text-black outline-none"
      />
      <div className="flex h-full items-center bg-gray-100 px-4 text-[10px] font-black uppercase tracking-widest text-gray-500 border-l border-gray-200">
        {suffix}
      </div>
    </div>
  );
}

function MiniModule({ label, active, onClick, icon: Icon }) {
  return (
    <button
      onClick={onClick}
      className={`group relative flex flex-col items-center justify-center gap-3 rounded-xl border p-4 transition-all duration-300 ${
        active
          ? 'border-[#ffb800]/30 bg-[#ffb800]/5 shadow-[0_0_20px_rgba(255,184,0,0.1)]'
          : 'border-white/5 bg-white/[0.02] hover:bg-white/[0.05]'
      }`}
    >
      <div className={`flex h-12 w-12 items-center justify-center rounded-lg transition-colors ${
        active ? 'bg-[#ffb800] text-black' : 'bg-[#25282f] text-gray-500 group-hover:text-gray-300'
      }`}>
        {Icon && <Icon size={20} />}
      </div>
      <div className="text-center">
        <p className={`text-[10px] font-black uppercase tracking-widest ${active ? 'text-[#ffb800]' : 'text-gray-500 group-hover:text-gray-400'}`}>
          {label}
        </p>
        <p className={`mt-1 text-[8px] font-bold uppercase tracking-widest ${active ? 'text-[#ffb800]/60' : 'text-gray-600'}`}>
          {active ? 'Active' : 'Inactive'}
        </p>
      </div>
    </button>
  );
}

export default function AppSettings() {
  const {
    oteoLevel2Enabled,
    oteoLevel3Enabled,
    oteoWarmupBars,
    oteoCooldownBars,
    ghostAmount,
    autoGhostEnabled,
    autoGhostExpirationSeconds,
    autoGhostMaxConcurrentTrades,
    autoGhostPerAssetCooldownSeconds,
    autoGhostMinimumPayout,
    ghostIcon,
    maxDailyLoss,
    maxTradesPerSession,
    stopOnLossStreak,
    aiModel,
    showManipulationAlerts,
    showSignalConfidence,
    autoFocusOnSignal,
    setOteoLevel2Enabled,
    setOteoLevel3Enabled,
    setOteoWarmupBars,
    setOteoCooldownBars,
    setGhostAmount,
    setAutoGhostEnabled,
    setAutoGhostExpirationSeconds,
    setAutoGhostMaxConcurrentTrades,
    setAutoGhostPerAssetCooldownSeconds,
    setAutoGhostMinimumPayout,
    setGhostIcon,
    setMaxDailyLoss,
    setMaxTradesPerSession,
    setStopOnLossStreak,
    setAiModel,
    setShowManipulationAlerts,
    setShowSignalConfidence,
    setAutoFocusOnSignal,
    miniChartConfig,
    setMiniChartConfig,
    uiSoundsEnabled,
    setUiSoundsEnabled,
    tradingSoundsEnabled,
    setTradingSoundsEnabled,
  } = useSettingsStore();

  const [isGhostSelectorOpen, setIsGhostSelectorOpen] = useState(false);

  return (
    <div className="max-w-[1400px] mx-auto p-8 space-y-10">
      {/* Header Section */}
      <div className="flex items-end justify-between border-b border-white/5 pb-8">
        <div>
          <h1 className="text-4xl font-black uppercase tracking-tighter text-white">Global System Settings</h1>
          <p className="mt-2 text-sm font-medium text-gray-500">Configure core algorithmic layers and execution protocols.</p>
        </div>
        <div className="flex gap-4">
          <button className="flex items-center gap-2 rounded-lg bg-[#25282f] px-6 py-3 text-xs font-black uppercase tracking-widest text-gray-400 transition hover:bg-[#2d3139] hover:text-white border border-white/5">
            <RefreshCcw size={14} />
            Revert Changes
          </button>
          <button className="flex items-center gap-2 rounded-lg bg-[#ffb800] px-8 py-3 text-xs font-black uppercase tracking-widest text-black transition hover:bg-[#ffc833] shadow-[0_4px_20px_rgba(255,184,0,0.3)]">
            <Save size={14} />
            Commit Protocol
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Left Column - OTEO & Auto-Ghost */}
        <div className="col-span-12 lg:col-span-7 space-y-6">
          
          {/* OTEO SIGNAL LAYER */}
          <SectionCard 
            title="OTEO Signal Layer" 
            subtitle="Primary signal detection engine with multi-layered verification."
            icon={Target}
            toggle={oteoLevel2Enabled}
            onToggle={setOteoLevel2Enabled}
          >
            <div className="space-y-6">
              <InputGroup label="Confidence Levels">
                <div className="flex gap-3">
                  {['Level 1', 'Level 2', 'Level 3 (AI)'].map((level, idx) => {
                    const isActive = idx === 0 || (idx === 1 && oteoLevel2Enabled) || (idx === 2 && oteoLevel3Enabled);
                    const isSelectable = idx > 0;
                    return (
                      <button
                        key={level}
                        onClick={() => {
                          if (idx === 1) setOteoLevel2Enabled(!oteoLevel2Enabled);
                          if (idx === 2) setOteoLevel3Enabled(!oteoLevel3Enabled);
                        }}
                        disabled={!isSelectable}
                        className={`flex-1 rounded-lg border py-4 text-[10px] font-black uppercase tracking-widest transition-all ${
                          isActive 
                            ? 'border-[#ffb800] bg-[#ffb800]/10 text-[#ffb800] shadow-[0_0_15px_rgba(255,184,0,0.1)]' 
                            : 'border-white/5 bg-white/[0.02] text-gray-600 hover:border-white/10 hover:text-gray-400'
                        }`}
                      >
                        {level}
                      </button>
                    );
                  })}
                </div>
              </InputGroup>

              <div className="flex items-center justify-between pt-4 border-t border-white/5">
                <p className="text-[10px] font-black uppercase tracking-widest text-gray-600">Active_Nodes</p>
                <p className="text-[10px] font-black uppercase tracking-widest text-[#ffb800]">409 / 512</p>
              </div>
            </div>
          </SectionCard>

          {/* AUTO-GHOST TRADER */}
          <SectionCard 
            title="Auto-Ghost Trader" 
            subtitle="Automated simulation layer for background data harvesting."
            icon={Ghost}
            toggle={autoGhostEnabled}
            onToggle={setAutoGhostEnabled}
          >
            <div className="grid grid-cols-2 gap-6">
              <InputGroup label="Simulated Amount" description="Primary execution unit.">
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-xl font-black text-[#ffb800]">$</span>
                  <input
                    type="number"
                    value={ghostAmount}
                    onChange={(e) => setGhostAmount(e.target.value)}
                    className="h-14 w-full rounded-lg bg-white pl-10 pr-4 text-xl font-black text-black outline-none shadow-inner"
                  />
                </div>
              </InputGroup>

              <InputGroup label="Expiry Times" description="Fixed duration per entry.">
                <div className="relative">
                  <select
                    value={autoGhostExpirationSeconds}
                    onChange={(e) => setAutoGhostExpirationSeconds(Number(e.target.value))}
                    className="h-14 w-full appearance-none rounded-lg bg-[#25282f] px-4 pr-10 text-sm font-black uppercase tracking-widest text-white outline-none border border-white/5"
                  >
                    <option value={60}>M1 (60 Seconds)</option>
                    <option value={120}>M2 (120 Seconds)</option>
                    <option value={300}>M5 (300 Seconds)</option>
                  </select>
                  <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
                </div>
              </InputGroup>
            </div>

            <div className="space-y-4">
              <InputGroup label="Max Concurrent Trades" layout="horizontal" description="Simultaneous active ghost positions.">
                <span className="text-xl font-black text-white">{String(autoGhostMaxConcurrentTrades).padStart(2, '0')}</span>
              </InputGroup>
              <InputGroup label="Cooldown Per Asset" layout="horizontal" description="Rest period for individual asset identifiers.">
                <span className="text-xl font-black text-white">{autoGhostPerAssetCooldownSeconds}s</span>
              </InputGroup>
            </div>

            <button
              onClick={() => setIsGhostSelectorOpen(!isGhostSelectorOpen)}
              className="group flex w-full items-center justify-between rounded-xl bg-[#25282f]/50 p-6 border border-white/5 transition hover:bg-[#25282f]"
            >
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#1a1c22] border border-white/10 group-hover:border-[#ffb800]/30 transition-colors">
                  <img src={GHOST_OPTIONS.find(o => o.id === ghostIcon)?.src || ghostStatic} alt="Ghost" className="h-8 w-8 object-contain mix-blend-screen" />
                </div>
                <div className="text-left">
                  <p className="text-[11px] font-black uppercase tracking-widest text-white">Copy Ghost Signals Executions</p>
                  <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-gray-600">Double click triggered master sync</p>
                </div>
              </div>
              <div className={`h-6 w-6 rounded-full border-2 transition-all ${isGhostSelectorOpen ? 'border-[#ffb800] bg-[#ffb800]/10' : 'border-white/10'}`} />
            </button>

            {isGhostSelectorOpen && (
              <div className="grid grid-cols-8 gap-3 p-4 bg-[#1a1c22] rounded-xl border border-white/5 animate-in fade-in slide-in-from-top-2">
                {GHOST_OPTIONS.map((option) => (
                  <button
                    key={option.id}
                    onClick={() => setGhostIcon(option.id)}
                    className={`aspect-square rounded-lg border flex items-center justify-center transition-all ${
                      ghostIcon === option.id ? 'border-[#ffb800] bg-[#ffb800]/10' : 'border-white/5 bg-white/5 hover:bg-white/10'
                    }`}
                  >
                    <img src={option.src} alt={option.name} className="h-6 w-6 object-contain mix-blend-screen" />
                  </button>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        {/* Right Column - Risk & UI Config */}
        <div className="col-span-12 lg:col-span-5 space-y-6">
          
          {/* RISK CONTROLS */}
          <SectionCard 
            title="Risk Controls" 
            subtitle="Guardrail protocols for automated execution cycles."
            icon={ShieldAlert}
            toggle={true} // Visual only for now as per design
            onToggle={() => {}}
          >
            <div className="grid grid-cols-2 gap-4">
              <InputGroup label="Warmup Bars" description="Bars required before signal confirmation.">
                <NumberInput 
                  value={oteoWarmupBars} 
                  onChange={setOteoWarmupBars} 
                  min={0} 
                  suffix="Units" 
                  icon={Activity}
                />
              </InputGroup>
              <InputGroup label="Cooldown Bars" description="Bars mandatory between consecutive trades.">
                <NumberInput 
                  value={oteoCooldownBars} 
                  onChange={setOteoCooldownBars} 
                  min={0} 
                  suffix="Units" 
                  icon={RefreshCcw}
                />
              </InputGroup>
            </div>
          </SectionCard>

          {/* CONFIDENCE & ALERTS */}
          <SectionCard 
            title="Confidence & Alerts" 
            subtitle="Real-time telemetry and validation parameters."
            icon={Zap}
          >
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <ShieldAlert size={16} className="text-[#ffb800]" />
                  <p className="text-[11px] font-black uppercase tracking-widest text-white">Manipulation Alerts</p>
                </div>
                <button
                  onClick={() => setShowManipulationAlerts(!showManipulationAlerts)}
                  className={`h-5 w-10 rounded-full transition-colors ${showManipulationAlerts ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
                >
                  <div className={`h-3 w-3 rounded-full bg-white transition-transform ${showManipulationAlerts ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>

              <InputGroup label="Confidence Threshold">
                <div className="flex items-center gap-4">
                  <input 
                    type="range" 
                    min="50" 
                    max="100" 
                    className="flex-1 accent-[#ffb800]"
                  />
                  <span className="text-2xl font-black text-white">85%</span>
                </div>
                <div className="mt-2 flex justify-between text-[8px] font-black uppercase tracking-widest text-gray-600">
                  <span>Low_Risk</span>
                  <span>Aggressive</span>
                </div>
              </InputGroup>

              <div className="flex items-center justify-between">
                <p className="text-[11px] font-black uppercase tracking-widest text-white">Auto-Focus on Signal</p>
                <button
                  onClick={() => setAutoFocusOnSignal(!autoFocusOnSignal)}
                  className={`h-5 w-10 rounded-full transition-colors ${autoFocusOnSignal ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
                >
                  <div className={`h-3 w-3 rounded-full bg-white transition-transform ${autoFocusOnSignal ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>

              <div className="rounded-xl bg-white/[0.02] p-6 text-center border border-white/5">
                <p className="text-[10px] font-black uppercase tracking-widest text-gray-500">Signal Integrity</p>
                <h4 className="mt-2 text-2xl font-black uppercase tracking-tighter text-[#ffb800]">Optimal</h4>
                <div className="mt-4 flex justify-center gap-1">
                  {[...Array(8)].map((_, i) => (
                    <div 
                      key={i} 
                      className="w-1.5 rounded-full bg-[#ffb800]" 
                      style={{ height: `${[12, 24, 18, 32, 28, 20, 14, 10][i]}px` }} 
                    />
                  ))}
                </div>
              </div>
            </div>
          </SectionCard>
        </div>

        {/* Bottom - MINI-CHART DISPLAY CONFIG */}
        <div className="col-span-12">
          <SectionCard 
            title="Mini-Chart Display Config" 
            subtitle="Configure telemetry overlays for active terminal views."
            icon={LayoutGrid}
          >
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                <Info size={14} className="text-gray-500" />
                <p className="text-xs font-medium text-gray-500">Enable or disable visual modules across the multi-chart dashboard.</p>
              </div>
              <div className="flex items-center gap-3 bg-[#25282f] px-4 py-2 rounded-lg border border-white/5">
                <p className="text-[10px] font-black uppercase tracking-widest text-gray-400">Global Visibility</p>
                <span className="text-[10px] font-black uppercase tracking-widest text-[#ffb800]">On</span>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <MiniModule 
                label="Mini-Sparklines" 
                active={miniChartConfig.showSparkline} 
                onClick={() => setMiniChartConfig({ showSparkline: !miniChartConfig.showSparkline })}
                icon={Activity}
              />
              <MiniModule 
                label="Gauges" 
                active={miniChartConfig.showGauge} 
                onClick={() => setMiniChartConfig({ showGauge: !miniChartConfig.showGauge })}
                icon={BarChart3}
              />
              <MiniModule 
                label="Live Stats (W/L)" 
                active={miniChartConfig.showStats} 
                onClick={() => setMiniChartConfig({ showStats: !miniChartConfig.showStats })}
                icon={BarChart3}
              />
              <MiniModule 
                label="Ghost Stats (W/L)" 
                active={true} // Placeholder
                onClick={() => {}}
                icon={Ghost}
              />
              <MiniModule 
                label="Regime" 
                active={miniChartConfig.showRegime} 
                onClick={() => setMiniChartConfig({ showRegime: !miniChartConfig.showRegime })}
                icon={Settings2}
              />
              <MiniModule 
                label="Pulse" 
                active={miniChartConfig.showManipulation} 
                onClick={() => setMiniChartConfig({ showManipulation: !miniChartConfig.showManipulation })}
                icon={Activity}
              />
            </div>
          </SectionCard>
        </div>
      </div>

      {/* Footer / Sounds Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-10 border-t border-white/5">
        <div className="rounded-xl bg-[#25282f]/30 p-6 flex items-center justify-between border border-white/5">
          <div className="flex items-center gap-4">
            <Volume2 className="text-gray-500" size={20} />
            <div>
              <p className="text-[11px] font-black uppercase tracking-widest text-white">Interface Sounds</p>
              <p className="text-[10px] font-medium text-gray-600 uppercase">Modern click effects for dashboard UI</p>
            </div>
          </div>
          <button
            onClick={() => setUiSoundsEnabled(!uiSoundsEnabled)}
            className={`h-5 w-10 rounded-full transition-colors ${uiSoundsEnabled ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
          >
            <div className={`h-3 w-3 rounded-full bg-white transition-transform ${uiSoundsEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
          </button>
        </div>
        <div className="rounded-xl bg-[#25282f]/30 p-6 flex items-center justify-between border border-white/5">
          <div className="flex items-center gap-4">
            <Bot className="text-gray-500" size={20} />
            <div>
              <p className="text-[11px] font-black uppercase tracking-widest text-white">Trading Events</p>
              <p className="text-[10px] font-medium text-gray-600 uppercase">Audible alerts for wins and losses</p>
            </div>
          </div>
          <button
            onClick={() => setTradingSoundsEnabled(!tradingSoundsEnabled)}
            className={`h-5 w-10 rounded-full transition-colors ${tradingSoundsEnabled ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
          >
            <div className={`h-3 w-3 rounded-full bg-white transition-transform ${tradingSoundsEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
          </button>
        </div>
      </div>
    </div>
  );
}
