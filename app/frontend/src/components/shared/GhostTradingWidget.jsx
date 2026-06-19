import { useState, useRef } from 'react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useRiskStore } from '../../stores/useRiskStore.js';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useToastStore } from '../../stores/useToastStore.js';
import { useTradingStore } from '../../stores/useTradingStore.js';
import { useNotificationStore } from '../../stores/useNotificationStore.js';
import { useLayoutStore } from '../../stores/useLayoutStore.js';
import { useAIStore } from '../../stores/useAIStore.js';
import { X, TrendingUp, TrendingDown, Target, Zap, ShieldAlert, Award, ChevronDown } from 'lucide-react';
import { Tooltip } from './StitchComponents.jsx';

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

const GHOST_ICONS = {
  'Ghost_Icon.png': ghostStatic,
  'bobble.gif': bobble,
  'bounce.gif': bounce,
  'cute-hop.gif': cuteHop,
  'deal-with-it.gif': dealWithIt,
  'drift.gif': drift,
  'elastic-corner-pinch.gif': elastic,
  'excited.gif': excited,
  'flag-wave.gif': flagWave,
  'hovering.gif': hovering,
  'party.gif': party,
  'radar-ping.gif': radarPing,
  'scanning.gif': scanning,
  'spin.gif': spin,
  'weird.gif': weird,
  'wobble.gif': wobble,
};

const formatInterval = (sec) => {
  if (sec < 60) return `${sec}s`;
  const mins = Math.floor(sec / 60);
  const remainingSecs = sec % 60;
  return remainingSecs > 0 ? `${mins}m ${remainingSecs}s` : `${mins}m`;
};

export default function GhostTradingWidget() {
  const autoGhostEnabled = useSettingsStore((s) => s.autoGhostEnabled);
  const ghostWidgetPosition = useSettingsStore((s) => s.ghostWidgetPosition);
  const setGhostWidgetPosition = useSettingsStore((s) => s.setGhostWidgetPosition);
  const ghostIcon = useSettingsStore((s) => s.ghostIcon);
  const ghostPnl = useRiskStore((s) => s.ghostPnl);
  const ghostWinRate = useRiskStore((s) => s.ghostWinRate);
  const ghostTotalTrades = useRiskStore((s) => s.ghostTotalTrades);
  const ghostMaxDrawdown = useRiskStore((s) => s.ghostMaxDrawdown);
  const ghostTrades = useRiskStore((s) => s.ghostTrades);

  // Settings from store
  const {
    ghostAmount,
    autoGhostExpirationSeconds,
    ghostMaxTradesPerTimeframe,
    ghostTimeframeSeconds,
    autoGhostCopyMode,
    ghostMinConfidence,
    ghostMinConfidenceEnabled,
    ghostMaxConfidence,
    ghostMaxConfidenceEnabled,
    autoGhostManipulationSeverityThreshold,
    autoGhostBlockOnManipulation,
    // New Z-Score + Regime gates for Ghost Protocol
    ghostMinZScore,
    ghostMinZScoreEnabled,
    ghostMaxZScore,
    ghostMaxZScoreEnabled,
    ghostRegimeGateEnabled,
    ghostAllowedRegimes,
    ghostRequireRegimeStable,
    setGhostMinZScore,
    setGhostMinZScoreEnabled,
    setGhostMaxZScore,
    setGhostMaxZScoreEnabled,
    setGhostRegimeGateEnabled,
    setGhostAllowedRegimes,
    setGhostRequireRegimeStable,
    setGhostAmount,
    setAutoGhostExpirationSeconds,
    setGhostMaxTradesPerTimeframe,
    setGhostTimeframeSeconds,
    setAutoGhostCopyMode,
    setGhostMinConfidence,
    setGhostMinConfidenceEnabled,
    setGhostMaxConfidence,
    setGhostMaxConfidenceEnabled,
    setAutoGhostManipulationSeverityThreshold,
    setAutoGhostBlockOnManipulation,
    // AI Advisory & Pulse settings
    oteoAiEnabled,
    aiPulseEnabled,
    aiPulseIntervalSeconds,
    aiTradeInterval,
    setAiPulseEnabled,
    setAiPulseIntervalSeconds,
    setAiTradeInterval,
    dontDisturbEnabled,
    setDontDisturbEnabled,
  } = useSettingsStore();

  const [requestingInsight, setRequestingInsight] = useState(false);

  const handleRequestManualInsight = async () => {
    if (requestingInsight) return;
    setRequestingInsight(true);
    try {
      const res = await fetch('/api/strategy/manual-advisory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(`Status ${res.status}`);
      useToastStore.getState().addToast({
        type: 'success',
        message: 'Manual AI Advisory triggered successfully',
        duration: 3000
      });
    } catch (err) {
      console.error('Failed to trigger manual insight:', err);
      useToastStore.getState().addToast({
        type: 'error',
        message: `Failed to trigger insight: ${err.message}`,
        duration: 3000
      });
    } finally {
      setRequestingInsight(false);
    }
  };

  const notifications = useNotificationStore((s) => s.notifications);
  const latestPulse = notifications.find(
    (n) => n.type === 'ai_pulse' || n.type === 'ai_advisory'
  );

  const handleUpdateGhostProtocol = (suggestions) => {
    if (!suggestions) return;

    if (suggestions.ghostMinConfidence !== undefined) setGhostMinConfidence(suggestions.ghostMinConfidence);
    if (suggestions.ghostMinConfidenceEnabled !== undefined) setGhostMinConfidenceEnabled(suggestions.ghostMinConfidenceEnabled);
    if (suggestions.ghostMaxConfidence !== undefined) setGhostMaxConfidence(suggestions.ghostMaxConfidence);
    if (suggestions.ghostMaxConfidenceEnabled !== undefined) setGhostMaxConfidenceEnabled(suggestions.ghostMaxConfidenceEnabled);
    
    if (suggestions.autoGhostManipulationSeverityThreshold !== undefined) setAutoGhostManipulationSeverityThreshold(suggestions.autoGhostManipulationSeverityThreshold);
    if (suggestions.autoGhostBlockOnManipulation !== undefined) setAutoGhostBlockOnManipulation(suggestions.autoGhostBlockOnManipulation);
    
    if (suggestions.ghostMinZScore !== undefined) setGhostMinZScore(suggestions.ghostMinZScore);
    if (suggestions.ghostMinZScoreEnabled !== undefined) setGhostMinZScoreEnabled(suggestions.ghostMinZScoreEnabled);
    if (suggestions.ghostMaxZScore !== undefined) setGhostMaxZScore(suggestions.ghostMaxZScore);
    if (suggestions.ghostMaxZScoreEnabled !== undefined) setGhostMaxZScoreEnabled(suggestions.ghostMaxZScoreEnabled);
    
    if (suggestions.ghostRegimeGateEnabled !== undefined) setGhostRegimeGateEnabled(suggestions.ghostRegimeGateEnabled);
    if (suggestions.ghostRequireRegimeStable !== undefined) setGhostRequireRegimeStable(suggestions.ghostRequireRegimeStable);
    if (suggestions.ghostAllowedRegimes !== undefined) setGhostAllowedRegimes(suggestions.ghostAllowedRegimes);
    
    if (suggestions.ghostAmount !== undefined) setGhostAmount(suggestions.ghostAmount);
    if (suggestions.autoGhostExpirationSeconds !== undefined) setAutoGhostExpirationSeconds(suggestions.autoGhostExpirationSeconds);
    if (suggestions.ghostMaxTradesPerTimeframe !== undefined) setGhostMaxTradesPerTimeframe(suggestions.ghostMaxTradesPerTimeframe);
    if (suggestions.ghostTimeframeSeconds !== undefined) setGhostTimeframeSeconds(suggestions.ghostTimeframeSeconds);

    let starredAddedCount = 0;
    if (Array.isArray(suggestions.whitelistAssets)) {
      const currentStarred = useAssetStore.getState().starredAssets;
      const nextStarred = [...currentStarred];
      suggestions.whitelistAssets.forEach((asset) => {
        if (!nextStarred.includes(asset)) {
          nextStarred.push(asset);
          starredAddedCount++;
        }
      });
      if (starredAddedCount > 0) {
        useAssetStore.getState().setStarredAssets(nextStarred);
      }
    }

    useToastStore.getState().addToast({
      type: 'success',
      message: `Ghost Protocol updated! Applied settings & starred ${starredAddedCount} assets.`,
      duration: 4000,
    });
  };

  const handleExtendToChat = (insightMessage) => {
    if (!insightMessage) return;
    const formattedDraft = `Regarding your recent AI Pulse update: "${insightMessage}"\n\nCould you give me more context on this setup, what confluences to look for, and why these Ghost Protocol values are recommended?`;
    useAIStore.getState().setDraft(formattedDraft);
    useLayoutStore.getState().setActiveView('ai');
    setIsOpen(false);
  };

  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('telemetry'); // 'telemetry' | 'settings'
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef({ startX: 0, startY: 0, initialX: 0, initialY: 0, isDragging: false });
  const containerRef = useRef(null);

  if (!autoGhostEnabled) return null;

  // We use the persisted position or default to {x: 0, y: 0}
  const position = ghostWidgetPosition || { x: 0, y: 0 };

  const handlePointerDown = (e) => {
    // Only left click
    if (e.button !== 0) return;
    
    // Prevent default to stop text selection/other drag behaviors
    e.preventDefault();
    
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initialX: position.x,
      initialY: position.y,
      isDragging: false,
    };

    const handlePointerMove = (moveEvent) => {
      const dx = moveEvent.clientX - dragRef.current.startX;
      const dy = moveEvent.clientY - dragRef.current.startY;
      
      // Threshold to distinguish between click and drag
      if (!dragRef.current.isDragging && (Math.abs(dx) > 3 || Math.abs(dy) > 3)) {
        dragRef.current.isDragging = true;
        setIsDragging(true);
      }
      
      if (dragRef.current.isDragging && containerRef.current) {
        // Direct DOM manipulation for buttery smooth dragging
        containerRef.current.style.transform = `translate(${dragRef.current.initialX + dx}px, ${dragRef.current.initialY + dy}px)`;
      }
    };

    const handlePointerUp = (upEvent) => {
      document.removeEventListener('pointermove', handlePointerMove);
      document.removeEventListener('pointerup', handlePointerUp);
      
      if (dragRef.current.isDragging) {
        // Save the final position to the store
        const dx = upEvent.clientX - dragRef.current.startX;
        const dy = upEvent.clientY - dragRef.current.startY;
        setGhostWidgetPosition({
          x: dragRef.current.initialX + dx,
          y: dragRef.current.initialY + dy
        });
      }

      // Small delay to prevent onClick from firing if we were dragging
      setTimeout(() => {
        setIsDragging(false);
        dragRef.current.isDragging = false;
      }, 0);
    };

    document.addEventListener('pointermove', handlePointerMove);
    document.addEventListener('pointerup', handlePointerUp);
  };

  const handleClick = () => {
    if (!isDragging && !dragRef.current.isDragging) {
      setIsOpen(!isOpen);
    }
  };

  const handleTradeClick = (trade) => {
    if (!trade.asset) return;

    const assetLabel = trade.asset.replace(/_otc$/i, ' OTC').replace(/_/g, '/');
    useAssetStore.getState().setSelectedAsset(trade.asset);

    useToastStore.getState().addToast({
      type: 'success',
      message: `Selected Ghost Asset: ${assetLabel.toUpperCase()}`,
      duration: 3000
    });

    if (autoGhostCopyMode === 'execute') {
      const direction = trade.direction ? trade.direction.toLowerCase() : 'call';
      const duration = trade.expirationSeconds || 60;

      useTradingStore.getState().setDirection(direction);
      useTradingStore.getState().setDuration(duration);
      useTradingStore.getState().executeTrade('pocket_option', trade.asset);

      useToastStore.getState().addToast({
        type: 'info',
        message: `Executing Live Trade: ${assetLabel.toUpperCase()} | ${direction.toUpperCase()} | ${duration}s`,
        duration: 3000
      });
    }
  };

  const recentTrades = ghostTrades.slice(-5).reverse();

  return (
    <div 
      ref={containerRef}
      className="absolute bottom-6 left-6 z-50"
      style={{ transform: `translate(${position.x}px, ${position.y}px)` }}
    >
      {/* The Popup */}
      {isOpen && (
        <div className="absolute bottom-16 left-0 mb-4 w-[360px] rounded-[20px] border border-white/5 bg-[#1a1c22] p-5 shadow-2xl backdrop-blur-xl origin-bottom-left animate-in fade-in zoom-in duration-200">
          <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-3">
            <div className="flex items-center gap-2 text-[#ffb800]">
              <Zap size={18} />
              <h3 className="text-sm font-black uppercase tracking-wider text-white">Auto Ghost Controller</h3>
              <button
                type="button"
                onClick={() => setDontDisturbEnabled(!dontDisturbEnabled)}
                className={`rounded border px-1.5 py-0.5 text-[8px] font-black uppercase tracking-wider transition-colors ${
                  dontDisturbEnabled
                    ? 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/20'
                    : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
                }`}
                title={dontDisturbEnabled ? "Notifications suspended — click to activate" : "Ghost Active — click to set Don't Disturb"}
              >
                {dontDisturbEnabled ? "Don't Disturb" : "Ghost Active"}
              </button>
              <Tooltip content="These stats reflect the simulated performance of the ghost trader module. Live account balances remain completely unaffected. Auto-Ghost mode is active on streamed nodes." />
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="rounded-lg p-1 text-gray-500 hover:bg-white/5 hover:text-white transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          {/* Navigation Tabs */}
          <div className="flex bg-[#25282f]/50 border border-white/5 p-1 rounded-xl mb-4 select-none">
            <button 
              className={`flex-1 text-[9px] font-black uppercase tracking-wider py-2 rounded-lg transition-all ${
                activeTab === 'telemetry' 
                  ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/20' 
                  : 'text-gray-500 hover:text-white border border-transparent'
              }`} 
              onClick={() => setActiveTab('telemetry')}
            >
              Stats
            </button>
            <button 
              className={`flex-1 text-[9px] font-black uppercase tracking-wider py-2 rounded-lg transition-all ${
                activeTab === 'settings' 
                  ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/20' 
                  : 'text-gray-500 hover:text-white border border-transparent'
              }`} 
              onClick={() => setActiveTab('settings')}
            >
              Protocol
            </button>
            <button 
              disabled={!oteoAiEnabled}
              className={`flex-1 text-[9px] font-black uppercase tracking-wider py-2 rounded-lg transition-all ${
                !oteoAiEnabled
                  ? 'text-gray-700 cursor-not-allowed opacity-40 border border-transparent'
                  : activeTab === 'ai' 
                    ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/20' 
                    : 'text-gray-500 hover:text-white border border-transparent'
              }`} 
              onClick={() => setActiveTab('ai')}
            >
              AI Tools
            </button>
          </div>

          {activeTab === 'telemetry' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <StatBox label="Ghost PnL" value={formatCurrency(ghostPnl)} tone={ghostPnl >= 0 ? 'emerald' : 'rose'} icon={ghostPnl >= 0 ? TrendingUp : TrendingDown} />
                <StatBox label="Win Rate" value={`${Math.round(ghostWinRate)}%`} tone="emerald" icon={Award} />
                <StatBox label="Ghost Trades" value={String(ghostTotalTrades)} tone="slate" icon={Target} />
                <StatBox label="Max DD" value={formatCurrency(-Math.abs(ghostMaxDrawdown))} tone="rose" icon={TrendingDown} />
              </div>

              {/* Recent Executed Trades */}
              <div className="border-t border-white/5 pt-3">
                <h4 className="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-2">Recent Executed Trades</h4>
                {recentTrades.length === 0 ? (
                  <p className="text-[10px] font-bold text-gray-600 uppercase italic py-4 text-center">No trades recorded</p>
                ) : (
                  <div className="space-y-1.5 max-h-[175px] overflow-y-auto pr-0.5 scrollbar-thin">
                    {recentTrades.map((trade, idx) => {
                      const assetLabel = trade.asset ? trade.asset.replace(/_otc$/i, ' OTC').replace(/_/g, '/') : 'UNKNOWN';
                      const directionLabel = trade.direction === 'call' ? 'CALL' : 'PUT';
                      const outcomeLabel = trade.outcome ? trade.outcome.toUpperCase() : 'PENDING';
                      
                      let pnlText = '$0.00';
                      if (trade.outcome === 'pending') {
                        pnlText = `$${Number(trade.stake || 0).toFixed(2)}`;
                      } else if (trade.pnl > 0) {
                        pnlText = `+$${trade.pnl.toFixed(2)}`;
                      } else if (trade.pnl < 0) {
                        pnlText = `-$${Math.abs(trade.pnl).toFixed(2)}`;
                      }

                      let outcomeColor = 'text-gray-500 bg-white/5 border-white/5';
                      if (trade.outcome === 'win') outcomeColor = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/25';
                      else if (trade.outcome === 'loss') outcomeColor = 'text-red-400 bg-red-500/10 border-red-500/25';
                      else if (trade.outcome === 'pending') outcomeColor = 'text-[#ffb800] bg-[#ffb800]/10 border-[#ffb800]/25 animate-pulse';

                      const directionColor = trade.direction === 'call' ? 'text-emerald-400' : 'text-red-400';

                      return (
                        <button
                          key={trade.id || idx}
                          onClick={() => handleTradeClick(trade)}
                          className="flex w-full items-center justify-between rounded-xl bg-[#25282f]/30 border border-white/5 p-2.5 transition hover:bg-[#25282f]/60 hover:border-[#ffb800]/20 text-left"
                          title={autoGhostCopyMode === 'execute' ? 'Click to Copy & Execute on Live' : 'Click to Select Asset'}
                        >
                          <div className="flex flex-col w-[110px] shrink-0">
                            <span className="text-[10px] font-black uppercase text-white tracking-wide">{assetLabel}</span>
                            <span className={`text-[8.5px] font-black uppercase ${directionColor} mt-0.5`}>
                              {directionLabel}
                            </span>
                          </div>

                          <div className="flex flex-col items-center justify-center shrink-0">
                            <span className="text-[7.5px] font-black uppercase tracking-widest text-gray-500">OTEO Score</span>
                            <span className="text-[11px] font-black text-[#ffb800] font-mono leading-none mt-0.5">
                              {trade.oteo_score != null ? `${Math.round(trade.oteo_score)}%` : '—'}
                            </span>
                          </div>

                          <div className="flex items-center justify-end gap-2 w-[110px] shrink-0">
                            <span className={`rounded-md border px-1.5 py-0.5 text-[8.5px] font-black uppercase tracking-wider ${outcomeColor}`}>
                              {outcomeLabel}
                            </span>
                            <span className={`text-[10px] font-black font-mono ${trade.pnl > 0 ? 'text-emerald-400' : trade.pnl < 0 ? 'text-red-400' : 'text-gray-500'}`}>
                              {pnlText}
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Copy Ghost Trades */}
              <div className="border-t border-white/5 pt-3">
                <label className="text-[9px] font-black uppercase tracking-wider text-gray-500 block mb-1">Copy Ghost Trades</label>
                <div className="flex rounded-lg bg-[#1a1c22] border border-white/5 p-0.5">
                  <button
                    type="button"
                    onClick={() => setAutoGhostCopyMode('copy')}
                    className={`flex-1 rounded-md py-1.5 text-[8.5px] font-black uppercase tracking-widest transition-all ${
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
                    className={`flex-1 rounded-md py-1.5 text-[8.5px] font-black uppercase tracking-widest transition-all ${
                      autoGhostCopyMode === 'execute'
                        ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/30'
                        : 'text-gray-500 hover:text-white'
                    }`}
                  >
                    Copy & Execute
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            /* Settings Controls Tab */
            <div className="space-y-4 max-h-[350px] overflow-y-auto pr-1 select-none scrollbar-thin">
              {/* Simulated Amount & Expiry Times */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[9px] font-black uppercase tracking-wider text-gray-500 block mb-1">Simulated Amount</label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-black text-[#ffb800]">$</span>
                    <input
                      type="number"
                      value={ghostAmount}
                      onChange={(e) => setGhostAmount(Number(e.target.value))}
                      className="h-9 w-full rounded-lg bg-[#25282f] pl-7 pr-2 text-xs font-black text-white outline-none border border-white/5"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-[9px] font-black uppercase tracking-wider text-gray-500 block mb-1">Expiry Times</label>
                  <div className="relative">
                    <select
                      value={autoGhostExpirationSeconds}
                      onChange={(e) => setAutoGhostExpirationSeconds(Number(e.target.value))}
                      className="h-9 w-full appearance-none rounded-lg bg-[#25282f] px-3 pr-8 text-[9px] font-black uppercase tracking-wider text-white outline-none border border-white/5"
                    >
                      <option value={15}>S15 (15s)</option>
                      <option value={30}>S30 (30s)</option>
                      <option value={60}>M1 (60s)</option>
                      <option value={120}>M2 (120s)</option>
                      <option value={300}>M5 (300s)</option>
                    </select>
                    <ChevronDown size={12} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
                  </div>
                </div>
              </div>

              {/* Timeframe Limit */}
              <div>
                <label className="text-[9px] font-black uppercase tracking-wider text-gray-500 block mb-1">Timeframe Limit</label>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex items-center gap-2 bg-[#25282f]/50 border border-white/5 rounded-lg h-9 px-2.5">
                    <span className="text-[8px] font-black uppercase tracking-wider text-gray-600 shrink-0">Max Trades</span>
                    <input 
                      type="number"
                      min={1}
                      max={100}
                      value={ghostMaxTradesPerTimeframe}
                      onChange={(e) => setGhostMaxTradesPerTimeframe(Number(e.target.value))}
                      className="w-full bg-transparent text-right text-xs font-black text-white outline-none"
                    />
                  </div>
                  <div className="flex items-center gap-2 bg-[#25282f]/50 border border-white/5 rounded-lg h-9 px-2.5">
                    <span className="text-[8px] font-black uppercase tracking-wider text-gray-600 shrink-0">Seconds</span>
                    <input 
                      type="number"
                      min={5}
                      max={3600}
                      value={ghostTimeframeSeconds}
                      onChange={(e) => setGhostTimeframeSeconds(Number(e.target.value))}
                      className="w-full bg-transparent text-right text-xs font-black text-white outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Confidence bounds sliders */}
              <div className="space-y-3 rounded-lg bg-[#25282f]/20 p-2.5 border border-white/5">
                <span className="text-[9px] font-black uppercase tracking-wider text-gray-400 block border-b border-white/5 pb-1 mb-1">Confidence Gate Bounds</span>
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-1.5 cursor-pointer select-none">
                      <input 
                        type="checkbox"
                        checked={ghostMinConfidenceEnabled}
                        onChange={(e) => setGhostMinConfidenceEnabled(e.target.checked)}
                        className="accent-[#ffb800] rounded h-3 w-3"
                      />
                      <span className={`text-[8.5px] font-black uppercase tracking-wider ${ghostMinConfidenceEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                        Min Bound
                      </span>
                    </label>
                    <span className={`text-[10px] font-black ${ghostMinConfidenceEnabled ? 'text-white' : 'text-gray-600'}`}>
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
                    className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer h-1 rounded-lg bg-[#25282f]"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-1.5 cursor-pointer select-none">
                      <input 
                        type="checkbox"
                        checked={ghostMaxConfidenceEnabled}
                        onChange={(e) => setGhostMaxConfidenceEnabled(e.target.checked)}
                        className="accent-[#ffb800] rounded h-3 w-3"
                      />
                      <span className={`text-[8.5px] font-black uppercase tracking-wider ${ghostMaxConfidenceEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                        Max Bound
                      </span>
                    </label>
                    <span className={`text-[10px] font-black ${ghostMaxConfidenceEnabled ? 'text-white' : 'text-gray-600'}`}>
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
                    className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer h-1 rounded-lg bg-[#25282f]"
                  />
                </div>
              </div>

              {/* Manipulation Severity slider */}
              <div className="space-y-2 rounded-lg bg-[#25282f]/20 p-2.5 border border-white/5">
                <span className="text-[9px] font-black uppercase tracking-wider text-gray-400 block border-b border-white/5 pb-1 mb-1">Manipulation Severity Gate</span>
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-1.5 cursor-pointer select-none">
                      <input 
                        type="checkbox"
                        checked={autoGhostBlockOnManipulation}
                        onChange={(e) => setAutoGhostBlockOnManipulation(e.target.checked)}
                        className="accent-[#ffb800] rounded h-3 w-3"
                      />
                      <span className={`text-[8.5px] font-black uppercase tracking-wider ${autoGhostBlockOnManipulation ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                        Max Allowed Severity
                      </span>
                    </label>
                    <span className={`text-[10px] font-black font-mono ${autoGhostBlockOnManipulation ? 'text-white' : 'text-gray-600'}`}>
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
                    className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer h-1 rounded-lg bg-[#25282f]"
                  />
                </div>
              </div>

              {/* Z-Score Gate Bounds — new for Ghost Protocol confluence */}
              <div className="space-y-3 rounded-lg bg-[#25282f]/20 p-2.5 border border-white/5">
                <span className="text-[9px] font-black uppercase tracking-wider text-gray-400 block border-b border-white/5 pb-1 mb-1">Z-Score Gate Bounds (Ghost Protocol)</span>
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-1.5 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={ghostMinZScoreEnabled}
                        onChange={(e) => setGhostMinZScoreEnabled(e.target.checked)}
                        className="accent-[#ffb800] rounded h-3 w-3"
                      />
                      <span className={`text-[8.5px] font-black uppercase tracking-wider ${ghostMinZScoreEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                        Min Z (avoid extreme negative deviation)
                      </span>
                    </label>
                    <span className={`text-[10px] font-black font-mono ${ghostMinZScoreEnabled ? 'text-white' : 'text-gray-600'}`}>
                      {ghostMinZScore.toFixed(1)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="-3"
                    max="1"
                    step="0.1"
                    disabled={!ghostMinZScoreEnabled}
                    value={ghostMinZScore}
                    onChange={(e) => setGhostMinZScore(Number(e.target.value))}
                    className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer h-1 rounded-lg bg-[#25282f]"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-1.5 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={ghostMaxZScoreEnabled}
                        onChange={(e) => setGhostMaxZScoreEnabled(e.target.checked)}
                        className="accent-[#ffb800] rounded h-3 w-3"
                      />
                      <span className={`text-[8.5px] font-black uppercase tracking-wider ${ghostMaxZScoreEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                        Max Z (cap positive deviation)
                      </span>
                    </label>
                    <span className={`text-[10px] font-black font-mono ${ghostMaxZScoreEnabled ? 'text-white' : 'text-gray-600'}`}>
                      {ghostMaxZScore.toFixed(1)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="-1"
                    max="3"
                    step="0.1"
                    disabled={!ghostMaxZScoreEnabled}
                    value={ghostMaxZScore}
                    onChange={(e) => setGhostMaxZScore(Number(e.target.value))}
                    className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer h-1 rounded-lg bg-[#25282f]"
                  />
                </div>
              </div>

              {/* Regime Gate — multi-confluence for Ghost Protocol */}
              <div className="space-y-2 rounded-lg bg-[#25282f]/20 p-2.5 border border-white/5">
                <div className="flex items-center justify-between border-b border-white/5 pb-1 mb-1">
                  <span className="text-[9px] font-black uppercase tracking-wider text-gray-400">Regime Gate (Ghost Protocol)</span>
                  <label className="flex items-center gap-1.5 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={ghostRegimeGateEnabled}
                      onChange={(e) => setGhostRegimeGateEnabled(e.target.checked)}
                      className="accent-[#ffb800] rounded h-3 w-3"
                    />
                    <span className={`text-[8.5px] font-black uppercase tracking-wider ${ghostRegimeGateEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                      {ghostRegimeGateEnabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </label>
                </div>

                <div className={`space-y-2 transition-opacity duration-200 ${ghostRegimeGateEnabled ? 'opacity-100' : 'opacity-40 pointer-events-none'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <label className="flex items-center gap-1.5 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        disabled={!ghostRegimeGateEnabled}
                        checked={ghostRequireRegimeStable}
                        onChange={(e) => setGhostRequireRegimeStable(e.target.checked)}
                        className="accent-[#ffb800] rounded h-3 w-3"
                      />
                      <span className={`text-[8.5px] font-black uppercase tracking-wider ${ghostRequireRegimeStable ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                        Require Regime Stable
                      </span>
                    </label>
                  </div>

                  <div>
                    <div className="text-[8px] font-black uppercase tracking-wider text-gray-500 mb-1">Allowed Regimes (click to toggle)</div>
                    <div className="flex flex-wrap gap-1.5">
                      {['RANGE_BOUND', 'TREND_REVERSAL', 'TREND_PULLBACK', 'STRONG_MOMENTUM', 'CHOPPY'].map(r => {
                        const active = (ghostAllowedRegimes || []).includes(r);
                        return (
                          <button
                            key={r}
                            type="button"
                            disabled={!ghostRegimeGateEnabled}
                            onClick={() => {
                              const current = ghostAllowedRegimes || [];
                              const next = active ? current.filter(x => x !== r) : [...current, r];
                              setGhostAllowedRegimes(next);
                            }}
                            className={`px-2 py-0.5 text-[8px] font-black uppercase tracking-wider rounded border transition ${active
                              ? 'bg-[#ffb800]/20 text-[#ffb800] border-[#ffb800]/40'
                              : 'bg-white/5 text-gray-400 border-white/10 hover:border-white/30'}`}
                          >
                            {r.replace('_', ' ')}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
                <div className="text-[8px] text-gray-500 mt-1">
                  {ghostRegimeGateEnabled
                    ? `Ghost only executes in selected regimes${ghostRequireRegimeStable ? ' when stable' : ''}.${(!ghostAllowedRegimes || ghostAllowedRegimes.length === 0) ? ' (All regimes allowed if empty)' : ''}`
                    : 'When disabled, selected chips and stability check do not block Auto-Ghost.'}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'ai' && (
            <div className="space-y-4 max-h-[350px] overflow-y-auto pr-1 select-none scrollbar-thin">
              {/* AI Pulse Enable/Disable */}
              <div className="space-y-2 rounded-lg bg-[#25282f]/20 p-2.5 border border-white/5">
                <div className="flex items-center justify-between border-b border-white/5 pb-1 mb-1">
                  <span className="text-[9px] font-black uppercase tracking-wider text-gray-400">AI Pulse Insights</span>
                  <label className="flex items-center gap-1.5 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={aiPulseEnabled}
                      onChange={(e) => setAiPulseEnabled(e.target.checked)}
                      className="accent-[#ffb800] rounded h-3 w-3"
                    />
                    <span className={`text-[8.5px] font-black uppercase tracking-wider ${aiPulseEnabled ? 'text-[#ffb800]' : 'text-gray-500'}`}>
                      {aiPulseEnabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </label>
                </div>

                <div className={`space-y-1 transition-opacity duration-200 ${aiPulseEnabled ? 'opacity-100' : 'opacity-40 pointer-events-none'}`}>
                  <div className="flex items-center justify-between">
                    <span className="text-[8.5px] font-black uppercase tracking-wider text-gray-500">
                      Pulse Interval
                    </span>
                    <span className="text-[10px] font-black font-mono text-white">
                      {formatInterval(aiPulseIntervalSeconds)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="3600"
                    step="10"
                    disabled={!aiPulseEnabled}
                    value={aiPulseIntervalSeconds}
                    onChange={(e) => setAiPulseIntervalSeconds(Number(e.target.value))}
                    className="w-full accent-[#ffb800] disabled:opacity-30 cursor-pointer h-1 rounded-lg bg-[#25282f]"
                  />
                </div>
              </div>

              {/* Trade Interval Suggestions */}
              <div className="space-y-2 rounded-lg bg-[#25282f]/20 p-2.5 border border-white/5">
                <span className="text-[9px] font-black uppercase tracking-wider text-gray-400 block border-b border-white/5 pb-1 mb-1">AI Suggestions Trigger</span>
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[8.5px] font-black uppercase tracking-wider text-gray-500">
                      Trigger Every
                    </span>
                    <span className="text-[10px] font-black font-mono text-white">
                      {aiTradeInterval} {aiTradeInterval === 1 ? 'Trade' : 'Trades'}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="50"
                    step="1"
                    value={aiTradeInterval}
                    onChange={(e) => setAiTradeInterval(Number(e.target.value))}
                    className="w-full accent-[#ffb800] cursor-pointer h-1 rounded-lg bg-[#25282f]"
                  />
                </div>
              </div>

              {/* Request Manual Advisory */}
              <div className="pt-2">
                <button
                  type="button"
                  onClick={handleRequestManualInsight}
                  disabled={requestingInsight}
                  className="w-full h-10 rounded-lg bg-[#ffb800] text-black font-black uppercase tracking-widest text-[9px] hover:bg-white transition-all disabled:opacity-50 flex items-center justify-center gap-1.5"
                >
                  <Zap size={12} className={requestingInsight ? 'animate-bounce' : ''} />
                  {requestingInsight ? 'Requesting Insight...' : 'Request Manual Insight'}
                </button>
              </div>

              {/* AI Pulse Insight Display */}
              {latestPulse && (
                <div className="space-y-3 border-t border-white/5 pt-3 mt-3">
                  <div className="rounded-xl bg-[#25282f]/30 border border-white/5 p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5 text-[#ffb800] text-[9px] font-black uppercase tracking-wider">
                        <Zap size={12} className="fill-current" />
                        AI Pulse Insight
                      </div>
                      <span className="text-[8px] font-bold text-gray-500 uppercase">
                        {new Date(latestPulse.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-[10px] text-gray-300 font-medium leading-relaxed mb-3 whitespace-pre-wrap select-text">
                      {latestPulse.message}
                    </p>
                    
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => handleExtendToChat(latestPulse.message)}
                        className="w-full h-7 rounded bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/5 text-[9px] font-black uppercase tracking-wider transition-colors flex items-center justify-center gap-1"
                      >
                        Extend to Chat
                      </button>
                    </div>
                  </div>

                  {/* Suggestions block */}
                  {latestPulse.suggestions && Object.keys(latestPulse.suggestions).length > 0 && (
                    <div className="rounded-xl bg-amber-500/5 border border-amber-500/10 p-3">
                      <div className="text-[#ffb800] text-[9px] font-black uppercase tracking-wider mb-2">
                        Proposed Ghost Protocol
                      </div>
                      
                      <div className="space-y-1.5 text-[9px] font-bold text-gray-400 mb-3 font-mono">
                        {latestPulse.suggestions.ghostMinConfidence !== undefined && (
                          <div>• MIN CONFIDENCE: <span className="text-white">{latestPulse.suggestions.ghostMinConfidence}%</span></div>
                        )}
                        {latestPulse.suggestions.ghostAllowedRegimes && (
                          <div>• REGIMES: <span className="text-white">{latestPulse.suggestions.ghostAllowedRegimes.join(', ')}</span></div>
                        )}
                        {latestPulse.suggestions.ghostMinZScore !== undefined && (
                          <div>• MIN Z-SCORE: <span className="text-white">{latestPulse.suggestions.ghostMinZScore}</span></div>
                        )}
                        {latestPulse.suggestions.autoGhostManipulationSeverityThreshold !== undefined && (
                          <div>• MANIP THRESHOLD: <span className="text-white">{latestPulse.suggestions.autoGhostManipulationSeverityThreshold}</span></div>
                        )}
                        {latestPulse.suggestions.whitelistAssets && latestPulse.suggestions.whitelistAssets.length > 0 && (
                          <div>• WHITELIST ASSETS: <span className="text-[#ffb800]">{latestPulse.suggestions.whitelistAssets.map(a => a.replace('_otc', ' OTC').toUpperCase()).join(', ')}</span></div>
                        )}
                      </div>

                      <button
                        type="button"
                        onClick={() => handleUpdateGhostProtocol(latestPulse.suggestions)}
                        className="w-full h-8 rounded bg-[#ffb800] hover:bg-white text-black font-black uppercase tracking-widest text-[9px] transition-all flex items-center justify-center gap-1.5 shadow-lg shadow-[#ffb800]/10"
                      >
                        <Zap size={11} className="fill-current" />
                        Update Ghost Protocol
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Floating Ghost Icon */}
      <button
        onClick={handleClick}
        onPointerDown={handlePointerDown}
        className={`relative flex h-14 w-14 items-center justify-center rounded-full border-2 bg-[#25282f]/90 shadow-lg shadow-[#ffb800]/10 transition-all ${
          isDragging 
            ? 'cursor-grabbing scale-110 shadow-[#ffb800]/30' 
            : 'cursor-grab hover:scale-110 hover:shadow-[#ffb800]/25'
        } ${isOpen ? 'border-[#ffb800]' : 'border-[#ffb800]/30 hover:border-[#ffb800]'}`}
        aria-label="Toggle Ghost Stats"
        title="Drag to move, click for Ghost Stats"
      >
        <img 
          src={GHOST_ICONS[ghostIcon] || GHOST_ICONS['drift.gif']} 
          alt="Ghost Trading" 
          className={`h-10 w-10 object-contain drop-shadow-md pointer-events-none ${ghostIcon === 'Ghost_Icon.png' ? 'mix-blend-screen' : ''}`}
        />
        {/* Pulsing indicator when closed to draw attention */}
        {!isOpen && (
          <span className="absolute top-0 right-0 flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#ffb800] opacity-75"></span>
            <span className="relative inline-flex h-3 w-3 rounded-full bg-[#ffb800]"></span>
          </span>
        )}
      </button>
    </div>
  );
}

function formatCurrency(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '$0.00';
  const sign = numeric > 0 ? '+' : numeric < 0 ? '-' : '';
  return `${sign}$${Math.abs(numeric).toFixed(2)}`;
}

function StatBox({ label, value, tone = 'slate', icon: Icon }) {
  const toneClasses = {
    emerald: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400',
    rose: 'border-red-500/25 bg-red-500/10 text-red-400',
    slate: 'border-white/5 bg-[#25282f]/30 text-white',
  };

  return (
    <div className={`rounded-xl border p-3 ${toneClasses[tone]}`}>
      <div className="flex items-center gap-1.5 text-[8px] font-black uppercase tracking-widest opacity-60">
        {Icon && <Icon size={12} />}
        {label}
      </div>
      <div className="mt-1 text-base font-black tracking-tight font-mono leading-none">{value}</div>
    </div>
  );
}
