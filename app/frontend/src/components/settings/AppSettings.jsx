/**
 * AppSettings — Global System Settings following the Stitch Design Reference.
 */
import { useState } from 'react';
import {
  Target, Bot, Ghost, Gauge, Volume2, LayoutGrid,
  ChevronDown, ShieldAlert, Activity, Zap,
  RefreshCcw, Save, Timer, TrendingUp, Eye, Layers
} from 'lucide-react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { SectionCard, InputGroup, NumberInput, MiniModule, Tooltip } from '../shared/StitchComponents.jsx';
import { AiChipIcon } from '../layout/TopBar.jsx';

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

export default function AppSettings() {
  const {
    oteoLevel2Enabled,
    oteoLevel3Enabled,
    oteoAiEnabled,
    oteoWarmupBars,
    oteoCooldownBars,
    ghostAmount,
    autoGhostEnabled,
    autoGhostCopyMode,
    autoGhostExpirationSeconds,
    autoGhostMinimumPayout,
    autoGhostManipulationSeverityThreshold,
    autoGhostBlockOnManipulation,
    ghostIcon,
    aiModel,
    aiDevMode,
    showManipulationAlerts,
    showSignalConfidence,
    autoFocusOnSignal,
    setOteoLevel2Enabled,
    setOteoLevel3Enabled,
    setOteoAiEnabled,
    setOteoWarmupBars,
    setOteoCooldownBars,
    setGhostAmount,
    setAutoGhostEnabled,
    setAutoGhostCopyMode,
    setAutoGhostExpirationSeconds,
    setAutoGhostMinimumPayout,
    setAutoGhostManipulationSeverityThreshold,
    setAutoGhostBlockOnManipulation,
    setGhostIcon,
    setAiModel,
    setAiDevMode,
    setShowManipulationAlerts,
    setShowSignalConfidence,
    setAutoFocusOnSignal,
    assetAutoRefreshEnabled,
    setAssetAutoRefreshEnabled,
    assetAutoRefreshInterval,
    setAssetAutoRefreshInterval,
    miniChartConfig,
    setMiniChartConfig,
    uiSoundsEnabled,
    setUiSoundsEnabled,
    tradingSoundsEnabled,
    setTradingSoundsEnabled,
    showGlobalTimer,
    setShowGlobalTimer,

    // Advanced Ghost Settings
    ghostMaxTradesPerTimeframe,
    ghostTimeframeSeconds,
    ghostMinConfidence,
    ghostMinConfidenceEnabled,
    ghostMaxConfidence,
    ghostMaxConfidenceEnabled,
    setGhostMaxTradesPerTimeframe,
    setGhostTimeframeSeconds,
    setGhostMinConfidence,
    setGhostMinConfidenceEnabled,
    setGhostMaxConfidence,
    setGhostMaxConfidenceEnabled,
  } = useSettingsStore();

  const [isGhostSelectorOpen, setIsGhostSelectorOpen] = useState(false);

  return (
    <div className="max-w-[1400px] mx-auto p-8 space-y-8">
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

      {/* Quick Toggles — Interface Sounds, Trading Events, Global Timer Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl bg-[#25282f]/30 p-5 flex items-center justify-between border border-white/5">
          <div className="flex items-center gap-4">
            <Volume2 className="text-gray-500" size={20} />
            <div className="flex items-center gap-1.5">
              <p className="text-[11px] font-black uppercase tracking-widest text-white">Interface Sounds</p>
              <Tooltip content="Modern click sound effects triggered during user interaction" />
            </div>
          </div>
          <button
            onClick={() => setUiSoundsEnabled(!uiSoundsEnabled)}
            className={`h-5 w-10 rounded-full transition-colors ${uiSoundsEnabled ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
          >
            <div className={`h-3 w-3 rounded-full bg-white transition-transform ${uiSoundsEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
          </button>
        </div>
        <div className="rounded-xl bg-[#25282f]/30 p-5 flex items-center justify-between border border-white/5">
          <div className="flex items-center gap-4">
            <Bot className="text-gray-500" size={20} />
            <div className="flex items-center gap-1.5">
              <p className="text-[11px] font-black uppercase tracking-widest text-white">Trading Events</p>
              <Tooltip content="Audible alerts triggered on trade wins and losses" />
            </div>
          </div>
          <button
            onClick={() => setTradingSoundsEnabled(!tradingSoundsEnabled)}
            className={`h-5 w-10 rounded-full transition-colors ${tradingSoundsEnabled ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
          >
            <div className={`h-3 w-3 rounded-full bg-white transition-transform ${tradingSoundsEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
          </button>
        </div>
        <div className="rounded-xl bg-[#25282f]/30 p-5 flex items-center justify-between border border-white/5">
          <div className="flex items-center gap-4">
            <Timer className="text-gray-500" size={20} />
            <div className="flex items-center gap-1.5">
              <p className="text-[11px] font-black uppercase tracking-widest text-white">Global Timer Bar</p>
              <Tooltip content="Universal UTC Clock and stopwatch stopwatch tracker shown at the bottom of the layout" />
            </div>
          </div>
          <button
            onClick={() => setShowGlobalTimer(!showGlobalTimer)}
            className={`h-5 w-10 rounded-full transition-colors ${showGlobalTimer ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
          >
            <div className={`h-3 w-3 rounded-full bg-white transition-transform ${showGlobalTimer ? 'translate-x-6' : 'translate-x-1'}`} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - OTEO Engine & AI Model settings */}
        <div className="space-y-6">
          
          {/* OTEO SIGNAL LAYER */}
          <SectionCard 
            title="OTEO Signal Layer" 
            subtitle="Primary signal detection engine with multi-layered verification."
            icon={Target}
            toggle={oteoLevel2Enabled}
            onToggle={setOteoLevel2Enabled}
          >
            <div className="space-y-6">
              <InputGroup label="Confidence Levels" tooltip="Set confidence verification thresholds for OTEO signal filtration">
                <div className="flex items-stretch gap-3">
                  <div className="flex flex-1 gap-3">
                    {['Level 1', 'Level 2', 'Level 3'].map((level, idx) => {
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
                  <button
                    onClick={() => setOteoAiEnabled(!oteoAiEnabled)}
                    title={oteoAiEnabled ? 'AI Layer enabled — click to disable' : 'AI Layer disabled — click to enable'}
                    className={`flex w-14 items-center justify-center rounded-lg border transition-all duration-350 ${
                      oteoAiEnabled 
                        ? 'border-[#ffb800]/40 bg-[#ffb800]/10 shadow-[0_0_15px_rgba(255,184,0,0.12)] scale-105' 
                        : 'border-white/5 bg-[#25282f]/30 hover:border-white/10 hover:bg-[#25282f]/50'
                    }`}
                  >
                    <div className={oteoAiEnabled ? '' : 'grayscale opacity-40'}>
                      <AiChipIcon size={34} />
                    </div>
                  </button>
                </div>
              </InputGroup>

              {/* Converted Risk Controls to inline parameters under OTEO */}
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/5">
                <InputGroup label="Warmup Bars" tooltip="Number of historic candle bars required before signal confirmation logic evaluates">
                  <NumberInput 
                    value={oteoWarmupBars} 
                    onChange={setOteoWarmupBars} 
                    min={0} 
                    suffix="Units" 
                    icon={Activity}
                  />
                </InputGroup>
                <InputGroup label="Cooldown Bars" tooltip="Mandatory rest bars required between consecutive signal trades">
                  <NumberInput 
                    value={oteoCooldownBars} 
                    onChange={setOteoCooldownBars} 
                    min={0} 
                    suffix="Units" 
                    icon={RefreshCcw}
                  />
                </InputGroup>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-white/5">
                <p className="text-[10px] font-black uppercase tracking-widest text-gray-600">Active_Nodes</p>
                <p className="text-[10px] font-black uppercase tracking-widest text-[#ffb800]">409 / 512</p>
              </div>
            </div>
          </SectionCard>

          {/* AI INTEGRATION & CONFIG */}
          <SectionCard 
            title="AI Integration & Feeds" 
            subtitle="Configure machine learning filters and asset catalog options."
            icon={Zap}
          >
            <div className="space-y-6">
              <InputGroup label="AI Model Select" tooltip="Model selector for signal refinement and trade confirmation">
                <div className="relative">
                  <select
                    value={aiModel}
                    onChange={(e) => setAiModel(e.target.value)}
                    className="h-14 w-full appearance-none rounded-lg bg-[#25282f] px-4 pr-10 text-xs font-black uppercase tracking-widest text-white outline-none border border-white/5"
                  >
                    <option value="grok-4-1-fast-non-reasoning">Grok 4.1 Fast (Standard)</option>
                    <option value="grok-4-1-reasoning">Grok 4.1 Reasoning (High Confidence)</option>
                    <option value="grok-4-agentic">Grok 4 Agentic (Experimental)</option>
                  </select>
                  <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
                </div>
              </InputGroup>

              <div className="flex items-center justify-between rounded-xl bg-white/[0.02] border border-white/5 p-4">
                <div className="flex flex-col text-left">
                  <div className="flex items-center gap-2">
                    <p className="text-[10px] font-black uppercase tracking-widest text-white">Developer Mode</p>
                    <Tooltip content="Enable developer mode to query Grok for platform upgrades, code design, and prompt analysis." />
                  </div>
                  <p className="mt-1 text-[9px] text-gray-500 font-medium">Chat with Grok about project insights and feature implementations.</p>
                </div>
                <button
                  onClick={() => setAiDevMode(!aiDevMode)}
                  className={`h-5 w-10 rounded-full transition-colors shrink-0 ${aiDevMode ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
                >
                  <div className={`h-3 w-3 rounded-full bg-white transition-transform ${aiDevMode ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center justify-between rounded-xl bg-white/[0.02] border border-white/5 p-4">
                  <div className="flex items-center gap-2">
                    <p className="text-[10px] font-black uppercase tracking-widest text-white">Auto-Focus</p>
                    <Tooltip content="Auto-switch active chart display tab on new incoming signals" />
                  </div>
                  <button
                    onClick={() => setAutoFocusOnSignal(!autoFocusOnSignal)}
                    className={`h-5 w-10 rounded-full transition-colors ${autoFocusOnSignal ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
                  >
                    <div className={`h-3 w-3 rounded-full bg-white transition-transform ${autoFocusOnSignal ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>

                <div className="flex items-center justify-between rounded-xl bg-white/[0.02] border border-white/5 p-4">
                  <div className="flex items-center gap-2">
                    <p className="text-[10px] font-black uppercase tracking-widest text-white">Auto-Refresh</p>
                    <Tooltip content="Automatically poll and refresh asset catalog list payouts in the background" />
                  </div>
                  <button
                    onClick={() => setAssetAutoRefreshEnabled(!assetAutoRefreshEnabled)}
                    className={`h-5 w-10 rounded-full transition-colors ${assetAutoRefreshEnabled ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
                  >
                    <div className={`h-3 w-3 rounded-full bg-white transition-transform ${assetAutoRefreshEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>
              </div>

              {assetAutoRefreshEnabled && (
                <InputGroup label="Auto-Refresh Interval" tooltip="Frequency of asset catalog background poll actions">
                  <div className="flex rounded-lg bg-[#1a1c22] border border-white/5 p-1">
                    {[
                      { value: 15, label: '15 SEC' },
                      { value: 30, label: '30 SEC' },
                      { value: 60, label: '1 MIN' },
                    ].map((preset) => (
                      <button
                        key={preset.value}
                        type="button"
                        onClick={() => setAssetAutoRefreshInterval(preset.value)}
                        className={`flex-1 rounded-md py-2 text-[10px] font-black uppercase tracking-widest transition-all ${
                          assetAutoRefreshInterval === preset.value
                            ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/30'
                            : 'text-gray-500 hover:text-white'
                        }`}
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>
                </InputGroup>
              )}
            </div>
          </SectionCard>

          {/* MINI-CHART DISPLAY CONFIG */}
          <SectionCard 
            title="Mini-Chart Display Config" 
            subtitle="Configure telemetry overlays for active terminal views."
            icon={LayoutGrid}
            badge="Global On"
          >
            <div className="grid grid-cols-3 gap-3">
              <MiniModule 
                label="Mini-Sparklines" 
                active={miniChartConfig.showSparkline} 
                onClick={() => setMiniChartConfig({ showSparkline: !miniChartConfig.showSparkline })}
                icon={Activity}
                compact={true}
              />
              <MiniModule 
                label="Gauges" 
                active={miniChartConfig.showGauge} 
                onClick={() => setMiniChartConfig({ showGauge: !miniChartConfig.showGauge })}
                icon={Gauge}
                compact={true}
              />
              <MiniModule 
                label="Live Stats (W/L)" 
                active={miniChartConfig.showStats} 
                onClick={() => setMiniChartConfig({ showStats: !miniChartConfig.showStats })}
                icon={TrendingUp}
                compact={true}
              />
              <MiniModule 
                label="Gauge on Hover" 
                active={miniChartConfig.gaugeOnHover} 
                onClick={() => setMiniChartConfig({ gaugeOnHover: !miniChartConfig.gaugeOnHover })}
                icon={Eye}
                compact={true}
              />
              <MiniModule 
                label="Regime" 
                active={miniChartConfig.showRegime} 
                onClick={() => setMiniChartConfig({ showRegime: !miniChartConfig.showRegime })}
                icon={Layers}
                compact={true}
              />
              <MiniModule 
                label="Pulse" 
                active={miniChartConfig.showManipulation} 
                onClick={() => setMiniChartConfig({ showManipulation: !miniChartConfig.showManipulation })}
                icon={Zap}
                compact={true}
              />
            </div>
          </SectionCard>
        </div>

        {/* Right Column - Simulator Configuration & Dual-Gates */}
        <div className="space-y-6">
          
          {/* AUTO-GHOST TRADER */}
          <SectionCard 
            title="Auto-Ghost Trader" 
            subtitle="Automated simulation layer for background data harvesting."
            icon={Ghost}
            toggle={autoGhostEnabled}
            onToggle={setAutoGhostEnabled}
          >
            {/* Ghost Avatar Selection */}
            <div className="mb-4">
              <button
                onClick={() => setIsGhostSelectorOpen(!isGhostSelectorOpen)}
                className="group flex w-full items-center justify-between rounded-xl bg-[#25282f]/50 p-4 border border-white/5 transition hover:bg-[#25282f]"
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#1a1c22] border border-white/10 group-hover:border-[#ffb800]/30 transition-colors">
                    <img src={GHOST_OPTIONS.find(o => o.id === ghostIcon)?.src || ghostStatic} alt="Ghost" className="h-8 w-8 object-contain mix-blend-screen" />
                  </div>
                  <div className="text-left">
                    <p className="text-[11px] font-black uppercase tracking-widest text-white">Ghost Widget Avatar</p>
                    <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-gray-600">Visual sprite indicator selection</p>
                  </div>
                </div>
                <div className={`h-6 w-6 rounded-full border-2 transition-all ${isGhostSelectorOpen ? 'border-[#ffb800] bg-[#ffb800]/10' : 'border-white/10'}`} />
              </button>

              {isGhostSelectorOpen && (
                <div className="grid grid-cols-8 gap-3 mt-3 p-4 bg-[#1a1c22] rounded-xl border border-white/5 animate-in fade-in slide-in-from-top-2">
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
            </div>

            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/5">
              <InputGroup label="Simulated Amount" tooltip="Fixed simulation stake amount per Ghost entry">
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

              <InputGroup label="Expiry Times" tooltip="Simulated contract expiration duration">
                <div className="relative">
                  <select
                    value={autoGhostExpirationSeconds}
                    onChange={(e) => setAutoGhostExpirationSeconds(Number(e.target.value))}
                    className="h-14 w-full appearance-none rounded-lg bg-[#25282f] px-4 pr-10 text-xs font-black uppercase tracking-widest text-white outline-none border border-white/5"
                  >
                    <option value={15}>S15 (15 Seconds)</option>
                    <option value={30}>S30 (30 Seconds)</option>
                    <option value={60}>M1 (60 Seconds)</option>
                    <option value={120}>M2 (120 Seconds)</option>
                    <option value={300}>M5 (300 Seconds)</option>
                  </select>
                  <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
                </div>
              </InputGroup>
            </div>

            {/* Timeframe Trade Limit Controls */}
            <div className="pt-4 border-t border-white/5">
              <InputGroup label="Timeframe Limit" tooltip="Set the maximum amount of simulator trades to execute within a specific timeframe (e.g. 2 max trades per 60s)">
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center gap-3 bg-white/[0.02] border border-white/5 rounded-lg h-14 px-3">
                    <span className="text-[10px] font-black uppercase tracking-wider text-gray-500">Max Trades</span>
                    <input 
                      type="number"
                      min={1}
                      max={100}
                      value={ghostMaxTradesPerTimeframe}
                      onChange={(e) => setGhostMaxTradesPerTimeframe(Number(e.target.value))}
                      className="w-full bg-transparent text-right text-lg font-black text-white outline-none"
                    />
                  </div>
                  <div className="flex items-center gap-3 bg-white/[0.02] border border-white/5 rounded-lg h-14 px-3">
                    <span className="text-[10px] font-black uppercase tracking-wider text-gray-500">Seconds</span>
                    <input 
                      type="number"
                      min={5}
                      max={3600}
                      value={ghostTimeframeSeconds}
                      onChange={(e) => setGhostTimeframeSeconds(Number(e.target.value))}
                      className="w-full bg-transparent text-right text-lg font-black text-white outline-none"
                    />
                  </div>
                </div>
              </InputGroup>
            </div>

            {/* Ghost Trade Copy Mode */}
            <InputGroup label="Copy Ghost Trades" tooltip="Copy simulation outcomes or automatically copy-execute live entries on live broker API">
              <div className="flex rounded-lg bg-[#1a1c22] border border-white/5 p-1">
                <button
                  type="button"
                  onClick={() => setAutoGhostCopyMode('copy')}
                  className={`flex-1 rounded-md py-2 text-[10px] font-black uppercase tracking-widest transition-all ${
                    autoGhostCopyMode === 'copy'
                      ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/30'
                      : 'text-gray-500 hover:text-white'
                  }`}
                >
                  Only Copy
                </button>
                <button
                  type="button"
                  onClick={() => setAutoGhostCopyMode('execute')}
                  className={`flex-1 rounded-md py-2 text-[10px] font-black uppercase tracking-widest transition-all ${
                    autoGhostCopyMode === 'execute'
                      ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/30'
                      : 'text-gray-500 hover:text-white'
                  }`}
                >
                  Copy & Execute
                </button>
              </div>
            </InputGroup>
          </SectionCard>

          {/* CONFIDENCE GATES & METRICS */}
          <SectionCard 
            title="Confidence Gates & Alerts" 
            subtitle="Real-time telemetry and validation parameters."
            icon={ShieldAlert}
          >
            <div className="space-y-6">
              
              {/* Dual Bounded Confidence Threshold Sliders */}
              <InputGroup label="Confidence Execution Window" tooltip="Specify the exact minimum and maximum confidence bounds for simulation execution entries. Enable bounds independently.">
                <div className="space-y-4 rounded-xl bg-white/[0.02] p-4 border border-white/5">
                  
                  {/* Minimum Gate */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 cursor-pointer select-none">
                        <input 
                          type="checkbox"
                          checked={ghostMinConfidenceEnabled}
                          onChange={(e) => setGhostMinConfidenceEnabled(e.target.checked)}
                          className="accent-[#ffb800] rounded"
                        />
                        <span className={`text-[10px] font-black uppercase tracking-wider ${ghostMinConfidenceEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                          Min Confidence Bound
                        </span>
                      </label>
                      <span className={`text-xs font-black ${ghostMinConfidenceEnabled ? 'text-white' : 'text-gray-600'}`}>
                        {ghostMinConfidence}%
                      </span>
                    </div>
                    <input 
                      type="range"
                      min="50"
                      max="100"
                      disabled={!ghostMinConfidenceEnabled}
                      value={ghostMinConfidence}
                      onChange={(e) => setGhostMinConfidence(Number(e.target.value))}
                      className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                    />
                  </div>

                  {/* Maximum Gate */}
                  <div className="space-y-2 pt-2 border-t border-white/5">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 cursor-pointer select-none">
                        <input 
                          type="checkbox"
                          checked={ghostMaxConfidenceEnabled}
                          onChange={(e) => setGhostMaxConfidenceEnabled(e.target.checked)}
                          className="accent-[#ffb800] rounded"
                        />
                        <span className={`text-[10px] font-black uppercase tracking-wider ${ghostMaxConfidenceEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                          Max Confidence Bound
                        </span>
                      </label>
                      <span className={`text-xs font-black ${ghostMaxConfidenceEnabled ? 'text-white' : 'text-gray-600'}`}>
                        {ghostMaxConfidence}%
                      </span>
                    </div>
                    <input 
                      type="range"
                      min="50"
                      max="100"
                      disabled={!ghostMaxConfidenceEnabled}
                      value={ghostMaxConfidence}
                      onChange={(e) => setGhostMaxConfidence(Number(e.target.value))}
                      className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                    />
                  </div>
                </div>
              </InputGroup>

              {/* Manipulation Severity Threshold Slider */}
              <InputGroup label="Manipulation Severity Gate" tooltip="Specify the maximum allowed severity score (0.0 to 1.0) before Auto-Ghost blocks the trade. Enable bounds to apply the threshold gate.">
                <div className="space-y-2 rounded-xl bg-white/[0.02] p-4 border border-white/5">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input 
                        type="checkbox"
                        checked={autoGhostBlockOnManipulation}
                        onChange={(e) => setAutoGhostBlockOnManipulation(e.target.checked)}
                        className="accent-[#ffb800] rounded"
                      />
                      <span className={`text-[10px] font-black uppercase tracking-wider ${autoGhostBlockOnManipulation ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                        Max Allowed Severity
                      </span>
                    </label>
                    <span className={`text-xs font-black font-mono ${autoGhostBlockOnManipulation ? 'text-white' : 'text-gray-600'}`}>
                      {autoGhostManipulationSeverityThreshold.toFixed(2)}
                    </span>
                  </div>
                  <input 
                    type="range"
                    min="0.0"
                    max="1.0"
                    step="0.05"
                    disabled={!autoGhostBlockOnManipulation}
                    value={autoGhostManipulationSeverityThreshold}
                    onChange={(e) => setAutoGhostManipulationSeverityThreshold(Number(e.target.value))}
                    className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                  />
                  <div className="text-[10px] font-medium text-gray-500 leading-normal">
                    Trades will execute if the current market manipulation severity is strictly below this threshold. Set to 0.0 to block on any manipulation.
                  </div>
                </div>
              </InputGroup>

              <div className="flex items-center justify-between border-t border-white/5 pt-4">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input 
                    type="checkbox"
                    checked={showManipulationAlerts}
                    onChange={(e) => setShowManipulationAlerts(e.target.checked)}
                    className="accent-[#ffb800] rounded"
                  />
                  <div className="flex items-center gap-1.5">
                    <span className={`text-[10px] font-black uppercase tracking-wider ${showManipulationAlerts ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                      Manipulation Alerts
                    </span>
                    <Tooltip content="Enable system notifications and sound alerts when volatile spikes or market manipulation index triggers" />
                  </div>
                </label>
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
      </div>

    </div>
  );
}
