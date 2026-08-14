/**
 * GhostSettings — Dedicated Auto-Ghost Trading and Gating Settings Panel.
 */
import { useState } from 'react';
import {
  Ghost, Target, ShieldAlert, Activity, RefreshCcw, Save, Trash2, Plus, Zap, AlertTriangle, Play, Pause, Award, ChevronDown
} from 'lucide-react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useToastStore } from '../../stores/useToastStore.js';
import { useNotificationStore } from '../../stores/useNotificationStore.js';
import { SectionCard, InputGroup, NumberInput, Tooltip } from '../shared/StitchComponents.jsx';
import AdaptiveExpirySettings from '../shared/AdaptiveExpirySettings.jsx';

export default function GhostSettings() {
  const {
    ghostAmount,
    autoGhostEnabled,
    autoGhostCopyMode,
    autoGhostExpirationSeconds,
    autoGhostMinimumPayout,
    autoGhostManipulationSeverityThreshold,
    autoGhostBlockOnManipulation,
    ghostMaxTradesPerTimeframe,
    ghostTimeframeSeconds,
    ghostMinConfidence,
    ghostMinConfidenceEnabled,
    ghostMaxConfidence,
    ghostMaxConfidenceEnabled,
    ghostMinZScore,
    ghostMinZScoreEnabled,
    ghostMaxZScore,
    ghostMaxZScoreEnabled,
    ghostRegimeGateEnabled,
    ghostAllowedRegimes,
    ghostRequireRegimeStable,
    minAdaptiveExpiry,
    adaptiveExpiryEnabled,
    ghostBlacklist,
    sidebarPayoutThreshold,
    autoGhostRsiCciEnabled,
    autoGhostVolatilityGateEnabled,
    minVolatilityScore,
    maxVolatilityScore,
    autoGhostLiquidityGateEnabled,
    minLiquidityScore,
    maxLiquidityScore,
    autoGhostAdxGateEnabled,
    autoGhostCciGateEnabled,
    autoGhostBayesianFilterEnabled,
    autoGhostBayesianMinProbability,

    setGhostAmount,
    setAutoGhostEnabled,
    setAutoGhostCopyMode,
    setAutoGhostExpirationSeconds,
    setAutoGhostMinimumPayout,
    setAutoGhostManipulationSeverityThreshold,
    setAutoGhostBlockOnManipulation,
    setGhostMaxTradesPerTimeframe,
    setGhostTimeframeSeconds,
    setGhostMinConfidence,
    setGhostMinConfidenceEnabled,
    setGhostMaxConfidence,
    setGhostMaxConfidenceEnabled,
    setGhostMinZScore,
    setGhostMinZScoreEnabled,
    setGhostMaxZScore,
    setGhostMaxZScoreEnabled,
    setGhostRegimeGateEnabled,
    setGhostAllowedRegimes,
    setGhostRequireRegimeStable,
    setGhostBlacklist,
    setSidebarPayoutThreshold,
    setAutoGhostRsiCciEnabled,
    setAutoGhostVolatilityGateEnabled,
    setMinVolatilityScore,
    setMaxVolatilityScore,
    setAutoGhostLiquidityGateEnabled,
    setMinLiquidityScore,
    setMaxLiquidityScore,
    setAutoGhostAdxGateEnabled,
    setAutoGhostCciGateEnabled,
    setAutoGhostBayesianFilterEnabled,
    setAutoGhostBayesianMinProbability,
    setGhostWidgetPosition,
  } = useSettingsStore();

  const { availableAssets, assetPayouts } = useAssetStore();
  const [selectedAssetToAdd, setSelectedAssetToAdd] = useState('');

  const handleAddBlacklist = () => {
    if (!selectedAssetToAdd) return;
    if (ghostBlacklist.includes(selectedAssetToAdd)) {
      useToastStore.getState().addToast({ type: 'info', message: 'Asset already blacklisted.' });
      return;
    }
    const nextBlacklist = [...ghostBlacklist, selectedAssetToAdd];
    setGhostBlacklist(nextBlacklist);
    useToastStore.getState().addToast({
      type: 'success',
      message: `${selectedAssetToAdd.replace('_otc', '').toUpperCase()} added to Ghost Blacklist.`,
    });
    setSelectedAssetToAdd('');
  };

  const handleRemoveBlacklist = (asset) => {
    const nextBlacklist = ghostBlacklist.filter((a) => a !== asset);
    setGhostBlacklist(nextBlacklist);
    useToastStore.getState().addToast({
      type: 'info',
      message: `${asset.replace('_otc', '').toUpperCase()} removed from Ghost Blacklist.`,
    });
  };

  const handleClearBlacklist = () => {
    setGhostBlacklist([]);
    useToastStore.getState().addToast({ type: 'success', message: 'Ghost Blacklist cleared.' });
  };

  const assetsToSelect = availableAssets.filter((a) => !ghostBlacklist.includes(a));

  return (
    <div className="max-w-[1400px] mx-auto p-8 space-y-8">
      {/* Header Section */}
      <div className="flex items-end justify-between border-b border-white/5 pb-8">
        <div>
          <h1 className="text-4xl font-black uppercase tracking-tighter text-white flex items-center gap-3">
            <Ghost className="text-[#ffb800] h-10 w-10" />
            Auto-Ghost Protocol Settings
          </h1>
          <p className="mt-2 text-sm font-medium text-gray-500">Configure background trade protocol, regime gates, and asset blacklists.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          {/* CORE CONTROL */}
          <SectionCard
            title="Auto-Ghost Core Parameters"
            subtitle="Base configuration settings for the background trade protocol engine."
            icon={Ghost}
            toggle={autoGhostEnabled}
            onToggle={setAutoGhostEnabled}
          >
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <InputGroup label="Simulated Amount" tooltip="Fixed protocol stake amount per Ghost entry">
                  <div className="relative">
                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-xl font-black text-[#ffb800]">$</span>
                    <input
                      type="number"
                      value={ghostAmount ?? ''}
                      onChange={(e) => {
                        const raw = e.target.value;
                        setGhostAmount(raw === '' ? '' : Number(raw));
                      }}
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

              {/* Minimum Payout */}
              <InputGroup label="Minimum Payout Percentage Gate" tooltip="Auto-Ghost will skip assets whose payout is strictly below this percentage.">
                <div className="space-y-2 rounded-xl bg-white/[0.02] p-4 border border-white/5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-black uppercase tracking-wider text-gray-500">Min Acceptable Payout</span>
                    <span className="text-sm font-black text-[#ffb800] font-mono">{autoGhostMinimumPayout}%</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="100"
                    step="1"
                    value={autoGhostMinimumPayout}
                    onChange={(e) => setAutoGhostMinimumPayout(Number(e.target.value))}
                    className="w-full accent-[#ffb800] cursor-pointer h-1 rounded-lg bg-[#25282f]"
                  />
                </div>
              </InputGroup>

              {/* Copy Mode */}
              <InputGroup label="Copy Ghost Trades" tooltip="Copy protocol outcomes or automatically copy-execute live entries on live broker API">
                <div className="flex rounded-lg bg-[#1a1c22] border border-white/5 p-1">
                  <button
                    type="button"
                    onClick={() => setAutoGhostCopyMode('copy')}
                    className={`flex-1 rounded-md py-3 text-[10px] font-black uppercase tracking-widest transition-all ${
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
                    className={`flex-1 rounded-md py-3 text-[10px] font-black uppercase tracking-widest transition-all ${
                      autoGhostCopyMode === 'execute'
                        ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/30'
                        : 'text-gray-500 hover:text-white'
                    }`}
                  >
                    Copy & Execute
                  </button>
                </div>
              </InputGroup>

              {/* Global Protocol & Widget Position Reset */}
              <div className="pt-2 border-t border-white/5 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-bold text-gray-300 block">Global Protocol Reset</span>
                  <span className="text-[9px] text-gray-500 block">Restores widget position & baseline calibration parameters</span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    useSettingsStore.getState().resetGhostControllerDefaults();
                    useNotificationStore.getState().clearAll();
                    useToastStore.getState().addToast({ type: 'success', message: 'Global Protocol Reset: Position, calibration defaults & AI Tools state restored.' });
                  }}
                  className="flex items-center gap-1.5 rounded-lg bg-white/5 border border-white/10 px-3 py-1.5 text-[9px] font-black uppercase tracking-wider text-gray-300 hover:bg-[#ffb800]/10 hover:text-[#ffb800] hover:border-[#ffb800]/30 transition-colors"
                >
                  <RefreshCcw size={12} />
                  Reset Controller Defaults
                </button>
              </div>
            </div>
          </SectionCard>

          {/* EXTENSIONS */}
          <SectionCard
            title="Extensions"
            subtitle="Core algorithmic boundaries and premium multi-scale extensions."
            icon={Activity}
          >
            <div className="space-y-6">
              {/* Adaptive Expiry Extension Slot */}
              <div className="space-y-3 rounded-lg bg-white/[0.02] p-4 border border-white/5">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                  <span className={`text-[10px] font-black uppercase tracking-wider ${adaptiveExpiryEnabled ? 'text-emerald-400' : 'text-gray-400'}`}>
                    Volatility-Adaptive Expiry Extension
                  </span>
                  <span className={`rounded px-1.5 py-0.5 text-[8px] font-black uppercase tracking-widest ${
                    adaptiveExpiryEnabled ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
                  }`}>
                    {adaptiveExpiryEnabled ? 'Active Plugin' : 'Disabled'}
                  </span>
                </div>
                <AdaptiveExpirySettings />
              </div>

              {/* RSI/CCI Momentum Confluence Gate */}
              <div className="space-y-3 rounded-lg bg-white/[0.02] p-4 border border-white/5">
                <div className="flex items-center justify-between pb-1">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={autoGhostRsiCciEnabled}
                      onChange={(e) => setAutoGhostRsiCciEnabled(e.target.checked)}
                      className="accent-[#ffb800] rounded"
                    />
                    <span className={`text-[10px] font-black uppercase tracking-wider ${autoGhostRsiCciEnabled ? 'text-amber-400' : 'text-gray-500'}`}>
                      RSI/CCI Momentum Confluence (Extension)
                    </span>
                  </label>
                </div>
                <div className="text-[10px] text-gray-500 leading-normal">
                  Vetoes entry signals if RSI(7) and CCI(9) on 30s candles are not parallel in the direction of the trade from extreme zones.
                </div>
              </div>

              {/* Cross-Asset Bayesian Win Probability Filter Extension */}
              <div className="space-y-3 rounded-lg bg-white/[0.02] p-4 border border-white/5">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={autoGhostBayesianFilterEnabled}
                      onChange={(e) => setAutoGhostBayesianFilterEnabled(e.target.checked)}
                      className="accent-[#ffb800] rounded"
                    />
                    <span className={`text-[10px] font-black uppercase tracking-wider ${autoGhostBayesianFilterEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                      Cross-Asset Bayesian Win Probability Filter
                    </span>
                  </label>
                  <span className={`rounded px-1.5 py-0.5 text-[8px] font-black uppercase tracking-widest ${
                    autoGhostBayesianFilterEnabled ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/20' : 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
                  }`}>
                    {autoGhostBayesianFilterEnabled ? `${autoGhostBayesianMinProbability}% Floor` : 'Disabled'}
                  </span>
                </div>
                <div className="space-y-2 pt-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-black uppercase tracking-wider text-gray-400">Min Win Probability Floor</span>
                    <span className="text-xs font-black text-white font-mono">{autoGhostBayesianMinProbability}%</span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="75"
                    step="1"
                    disabled={!autoGhostBayesianFilterEnabled}
                    value={autoGhostBayesianMinProbability}
                    onChange={(e) => setAutoGhostBayesianMinProbability(Number(e.target.value))}
                    className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer h-1.5 rounded-lg bg-[#25282f]"
                  />
                </div>
                <div className="text-[10px] text-gray-500 leading-normal italic">
                  Vetoes low-expectancy trade setups using Laplace-smoothed Naive Bayes computed over 13,700+ pre-seeded historical ghost trade signals.
                </div>
              </div>
            </div>
          </SectionCard>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* ASSET BLACKLIST CONTROL */}
          <SectionCard
            title="Ghost Asset Blacklist"
            subtitle="Manually exclude assets from protocol execution or let the dynamic payout scanner automatically filter them."
            icon={ShieldAlert}
            action={
              <button
                type="button"
                onClick={handleClearBlacklist}
                disabled={ghostBlacklist.length === 0}
                className="flex items-center justify-center p-2 rounded-lg text-gray-500 hover:bg-red-500/10 hover:text-red-400 disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-gray-500 transition-colors"
                title="Reset/Clear Blacklist"
              >
                <RefreshCcw size={16} />
              </button>
            }
          >
            <div className="space-y-4">
              {/* Manual Add Blacklist */}
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <select
                    value={selectedAssetToAdd}
                    onChange={(e) => setSelectedAssetToAdd(e.target.value)}
                    className="h-10 w-full appearance-none rounded-lg bg-[#25282f] px-3 pr-8 text-xs font-black uppercase tracking-wider text-white outline-none border border-white/5"
                  >
                    <option value="">-- Select Asset to Blacklist --</option>
                    {assetsToSelect.map((asset) => (
                      <option key={asset} value={asset}>
                        {asset.replace('_otc', '').toUpperCase()} ({(assetPayouts[asset] ? Math.round(assetPayouts[asset] * 100) : 0)}%)
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
                </div>
                <button
                  type="button"
                  onClick={handleAddBlacklist}
                  disabled={!selectedAssetToAdd}
                  className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#ffb800] text-black transition hover:bg-white disabled:opacity-40"
                >
                  <Plus size={16} />
                </button>
              </div>

              {/* Blacklisted items list */}
              {ghostBlacklist.length === 0 ? (
                <div className="text-center py-6 text-xs text-gray-600 italic uppercase">
                  No assets currently blacklisted
                </div>
              ) : (
                <div className="space-y-1.5 max-h-[180px] overflow-y-auto pr-1 scrollbar-thin">
                  {ghostBlacklist.map((asset) => {
                    const payout = assetPayouts[asset];
                    const belowSidebarPayout = payout !== undefined && payout * 100 < sidebarPayoutThreshold;

                    return (
                      <div
                        key={asset}
                        className="flex items-center justify-between rounded-xl bg-[#25282f]/30 border border-white/5 p-3 hover:border-red-500/20 transition-all"
                      >
                        <div className="flex flex-col">
                          <span className="text-xs font-black text-white uppercase tracking-wider">
                            {asset.replace('_otc', '').toUpperCase()}
                          </span>
                          <span className={`text-[8.5px] font-bold mt-0.5 uppercase flex items-center gap-1 ${
                            belowSidebarPayout ? 'text-red-400' : 'text-gray-500'
                          }`}>
                            {belowSidebarPayout ? <AlertTriangle size={10} /> : null}
                            Payout: {payout !== undefined ? `${Math.round(payout * 100)}%` : '—'} 
                            {belowSidebarPayout ? `(<${sidebarPayoutThreshold}% minimum)` : ''}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveBlacklist(asset)}
                          className="p-1.5 rounded-lg text-gray-500 hover:bg-red-500/10 hover:text-red-400 transition-colors"
                          title="Remove from blacklist"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </SectionCard>

          {/* ADVANCED GATING BOUNDARIES */}
          <SectionCard
            title="Algorithmic Gate Boundaries"
            subtitle="Regime stability checks, Z-Score deviation windows, and timeframe constraints."
            icon={ShieldAlert}
          >
            <div className="space-y-6">
              {/* Confidence Bounds */}
              <InputGroup label="Confidence Execution Window" tooltip="Specify the exact minimum and maximum confidence bounds for protocol execution entries. Enable bounds independently.">
                <div className="space-y-4 rounded-xl bg-white/[0.02] p-4 border border-white/5">
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
                      className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer"
                    />
                  </div>

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
                      className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer"
                    />
                  </div>
                </div>
              </InputGroup>

              {/* Z-Score Bounds */}
              <InputGroup label="Z-Score Gate Bounds" tooltip="Define active boundaries for statistical deviation.">
                <div className="space-y-4 rounded-xl bg-white/[0.02] p-4 border border-white/5">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={ghostMinZScoreEnabled}
                          onChange={(e) => setGhostMinZScoreEnabled(e.target.checked)}
                          className="accent-[#ffb800] rounded"
                        />
                        <span className={`text-[10px] font-black uppercase tracking-wider ${ghostMinZScoreEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                          Min Z-Score
                        </span>
                      </label>
                      <span className={`text-xs font-black font-mono ${ghostMinZScoreEnabled ? 'text-white' : 'text-gray-600'}`}>
                        {ghostMinZScore.toFixed(1)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="-3.0"
                      max="1.0"
                      step="0.1"
                      disabled={!ghostMinZScoreEnabled}
                      value={ghostMinZScore}
                      onChange={(e) => setGhostMinZScore(Number(e.target.value))}
                      className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer"
                    />
                  </div>

                  <div className="space-y-2 pt-2 border-t border-white/5">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={ghostMaxZScoreEnabled}
                          onChange={(e) => setGhostMaxZScoreEnabled(e.target.checked)}
                          className="accent-[#ffb800] rounded"
                        />
                        <span className={`text-[10px] font-black uppercase tracking-wider ${ghostMaxZScoreEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                          Max Z-Score
                        </span>
                      </label>
                      <span className={`text-xs font-black font-mono ${ghostMaxZScoreEnabled ? 'text-white' : 'text-gray-600'}`}>
                        {ghostMaxZScore.toFixed(1)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="-1.0"
                      max="3.0"
                      step="0.1"
                      disabled={!ghostMaxZScoreEnabled}
                      value={ghostMaxZScore}
                      onChange={(e) => setGhostMaxZScore(Number(e.target.value))}
                      className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer"
                    />
                  </div>
                </div>
              </InputGroup>

              {/* Regime Gates */}
              <InputGroup label="Regime Filter Gate" tooltip="Restrict execution entries only to selected regimes.">
                <div className="space-y-3 rounded-xl bg-white/[0.02] p-4 border border-white/5">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={ghostRegimeGateEnabled}
                        onChange={(e) => setGhostRegimeGateEnabled(e.target.checked)}
                        className="accent-[#ffb800] rounded"
                      />
                      <span className={`text-[10px] font-black uppercase tracking-wider ${ghostRegimeGateEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                        Enable Regime Filter
                      </span>
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        disabled={!ghostRegimeGateEnabled}
                        checked={ghostRequireRegimeStable}
                        onChange={(e) => setGhostRequireRegimeStable(e.target.checked)}
                        className="accent-[#ffb800] rounded disabled:opacity-30"
                      />
                      <span className={`text-[9px] font-black uppercase tracking-wider ${ghostRequireRegimeStable && ghostRegimeGateEnabled ? 'text-[#ffb800]' : 'text-gray-600'}`}>
                        Require Stable
                      </span>
                    </label>
                  </div>
                  {ghostRegimeGateEnabled && (
                    <div className="flex flex-wrap gap-1.5 pt-2 border-t border-white/5">
                      {['RANGE_BOUND', 'TREND_REVERSAL', 'TREND_PULLBACK', 'STRONG_MOMENTUM', 'CHOPPY'].map((r) => {
                        const active = (ghostAllowedRegimes || []).includes(r);
                        return (
                          <button
                            key={r}
                            type="button"
                            onClick={() => {
                              const current = ghostAllowedRegimes || [];
                              const next = active ? current.filter((x) => x !== r) : [...current, r];
                              setGhostAllowedRegimes(next);
                            }}
                            className={`px-2 py-1 text-[9px] font-black uppercase tracking-wider rounded border transition ${
                              active ? 'bg-[#ffb800]/20 text-[#ffb800] border-[#ffb800]/40' : 'bg-white/5 text-gray-400 border-white/10 hover:border-white/35'
                            }`}
                          >
                            {r.replace('_', ' ')}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </InputGroup>

              {/* Timeframe Limit */}
              <InputGroup label="Timeframe Limit" tooltip="Set the maximum amount of simulator trades to execute within a specific timeframe (e.g. 2 max trades per 60s)">
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center gap-3 bg-white/[0.02] border border-white/5 rounded-lg h-14 px-3">
                    <span className="text-[10px] font-black uppercase tracking-wider text-gray-500">Max Trades</span>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={ghostMaxTradesPerTimeframe ?? ''}
                      onChange={(e) => {
                        const raw = e.target.value;
                        setGhostMaxTradesPerTimeframe(raw === '' ? '' : Number(raw));
                      }}
                      className="w-full bg-transparent text-right text-lg font-black text-white outline-none"
                    />
                  </div>
                  <div className="flex items-center gap-3 bg-white/[0.02] border border-white/5 rounded-lg h-14 px-3">
                    <span className="text-[10px] font-black uppercase tracking-wider text-gray-500">Seconds</span>
                    <input
                      type="number"
                      min={5}
                      max={3600}
                      value={ghostTimeframeSeconds ?? ''}
                      onChange={(e) => {
                        const raw = e.target.value;
                        setGhostTimeframeSeconds(raw === '' ? '' : Number(raw));
                      }}
                      className="w-full bg-transparent text-right text-lg font-black text-white outline-none"
                    />
                  </div>
                </div>
              </InputGroup>

              {/* Manipulation severity */}
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
                    className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer"
                  />
                </div>
              </InputGroup>

              {/* Volatility Score Gate */}
              <InputGroup label="Volatility Score Gate" tooltip="Vetoes Auto-Ghost entries if the market's volatility score falls outside the selected bounds.">
                <div className="space-y-4 rounded-xl bg-white/[0.02] p-4 border border-white/5">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={autoGhostVolatilityGateEnabled}
                          onChange={(e) => setAutoGhostVolatilityGateEnabled(e.target.checked)}
                          className="accent-[#ffb800] rounded"
                        />
                        <span className={`text-[10px] font-black uppercase tracking-wider ${autoGhostVolatilityGateEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                          Enable Volatility Gate
                        </span>
                      </label>
                      <span className={`text-xs font-black font-mono ${autoGhostVolatilityGateEnabled ? 'text-white' : 'text-gray-600'}`}>
                        {minVolatilityScore}% - {maxVolatilityScore}%
                      </span>
                    </div>
                    {autoGhostVolatilityGateEnabled && (
                      <div className="space-y-3 pt-2 border-t border-white/5">
                        <div className="space-y-1">
                          <div className="flex justify-between text-[8px] text-gray-500">
                            <span>Min Volatility: {minVolatilityScore}%</span>
                            <span>Max Volatility: {maxVolatilityScore}%</span>
                          </div>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={maxVolatilityScore}
                            onChange={(e) => setMaxVolatilityScore(Number(e.target.value))}
                            className="w-full accent-[#ffb800] cursor-pointer"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </InputGroup>

              {/* Liquidity Score Gate */}
              <InputGroup label="Liquidity Score Gate" tooltip="Vetoes Auto-Ghost entries if the market's liquidity (sigmoid tick rate) falls outside the selected bounds.">
                <div className="space-y-4 rounded-xl bg-white/[0.02] p-4 border border-white/5">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={autoGhostLiquidityGateEnabled}
                          onChange={(e) => setAutoGhostLiquidityGateEnabled(e.target.checked)}
                          className="accent-[#ffb800] rounded"
                        />
                        <span className={`text-[10px] font-black uppercase tracking-wider ${autoGhostLiquidityGateEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                          Enable Liquidity Gate
                        </span>
                      </label>
                      <span className={`text-xs font-black font-mono ${autoGhostLiquidityGateEnabled ? 'text-white' : 'text-gray-600'}`}>
                        {minLiquidityScore}% - {maxLiquidityScore}%
                      </span>
                    </div>
                    {autoGhostLiquidityGateEnabled && (
                      <div className="space-y-3 pt-2 border-t border-white/5">
                        <div className="space-y-1">
                          <div className="flex justify-between text-[8px] text-gray-500">
                            <span>Min Liquidity: {minLiquidityScore}%</span>
                            <span>Max Liquidity: {maxLiquidityScore}%</span>
                          </div>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={maxLiquidityScore}
                            onChange={(e) => setMaxLiquidityScore(Number(e.target.value))}
                            className="w-full accent-[#ffb800] cursor-pointer"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </InputGroup>

              {/* Trend Risk Gates (ADX / CCI) */}
              <InputGroup label="Trend & Exhaustion Gates" tooltip="Advanced filters to avoid executing trades against strong trends or invalid momentum states.">
                <div className="space-y-4 rounded-xl bg-[#25282f]/20 border border-white/5 p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex flex-col">
                      <span className="text-[10px] font-black uppercase tracking-wider text-white">ADX Trend Gate</span>
                      <span className="text-[8px] text-gray-500 mt-0.5">Vetoes counter-trend setups under strong trending regimes.</span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={autoGhostAdxGateEnabled}
                        onChange={(e) => setAutoGhostAdxGateEnabled(e.target.checked)}
                        className="sr-only"
                      />
                      <div className={`w-9 h-5 rounded-full transition-colors relative ${
                        autoGhostAdxGateEnabled ? 'bg-[#ffb800]' : 'bg-[#25282f]'
                      }`}>
                        <div className={`absolute top-[2px] left-[2px] bg-white rounded-full h-4 w-4 transition-transform duration-200 ${
                          autoGhostAdxGateEnabled ? 'translate-x-4' : 'translate-x-0'
                        }`} />
                      </div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between border-t border-white/5 pt-4">
                    <div className="flex flex-col">
                      <span className="text-[10px] font-black uppercase tracking-wider text-white">CCI Extreme Gate</span>
                      <span className="text-[8px] text-gray-500 mt-0.5">Bypasses entries during misaligned CCI overbought/oversold extremes.</span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={autoGhostCciGateEnabled}
                        onChange={(e) => setAutoGhostCciGateEnabled(e.target.checked)}
                        className="sr-only"
                      />
                      <div className={`w-9 h-5 rounded-full transition-colors relative ${
                        autoGhostCciGateEnabled ? 'bg-[#ffb800]' : 'bg-[#25282f]'
                      }`}>
                        <div className={`absolute top-[2px] left-[2px] bg-white rounded-full h-4 w-4 transition-transform duration-200 ${
                          autoGhostCciGateEnabled ? 'translate-x-4' : 'translate-x-0'
                        }`} />
                      </div>
                    </label>
                  </div>
                </div>
              </InputGroup>
            </div>
          </SectionCard>


        </div>
      </div>
    </div>
  );
}
