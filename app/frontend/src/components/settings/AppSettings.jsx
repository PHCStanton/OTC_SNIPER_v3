/**
 * AppSettings — Global System Settings following the Stitch Design Reference.
 */
import { useState } from 'react';
import {
  Target, Bot, Ghost, Gauge, Volume2, LayoutGrid,
  ChevronDown, ShieldAlert, Activity, Zap,
  RefreshCcw, Save, Timer, TrendingUp, Eye, Layers, Bell
} from 'lucide-react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { SectionCard, InputGroup, NumberInput, MiniModule, Tooltip } from '../shared/StitchComponents.jsx';
import { AiChipIcon } from '../layout/TopBar.jsx';

export default function AppSettings() {
  const {
    oteoLevel2Enabled,
    oteoLevel3Enabled,
    oteoAiEnabled,
    oteoWarmupBars,
    oteoCooldownBars,
    autoFocusOnSignal,
    setOteoLevel2Enabled,
    setOteoLevel3Enabled,
    setOteoAiEnabled,
    setOteoWarmupBars,
    setOteoCooldownBars,
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
    notificationSoundsEnabled,
    setNotificationSoundsEnabled,
    showGlobalTimer,
    setShowGlobalTimer,
  } = useSettingsStore();

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

      {/* Quick Toggles — Interface Sounds, Notification Sounds, Trading Events, Global Timer Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
            <Bell className="text-gray-500" size={20} />
            <div className="flex items-center gap-1.5">
              <p className="text-[11px] font-black uppercase tracking-widest text-white">Notification Sounds</p>
              <Tooltip content="Audible alerts triggered when receiving AI advisory updates or system notices" />
            </div>
          </div>
          <button
            onClick={() => setNotificationSoundsEnabled(!notificationSoundsEnabled)}
            className={`h-5 w-10 rounded-full transition-colors ${notificationSoundsEnabled ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
          >
            <div className={`h-3 w-3 rounded-full bg-white transition-transform ${notificationSoundsEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
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
        {/* Column 1 - OTEO Engine & AI Model settings */}
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
        </div>

        {/* Column 2 - Focus, Refresh & Modular Display Configs */}
        <div className="space-y-6">
          {/* FOCUS & REFRESH CONFIG */}
          <SectionCard 
            title="Focus & Refresh Config" 
            subtitle="Configure automatic asset focusing on signals and catalog refresh behavior."
            icon={RefreshCcw}
          >
            <div className="space-y-6">
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
      </div>
    </div>
  );
}
