import { useState, useRef } from 'react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useRiskStore } from '../../stores/useRiskStore.js';
import { useAssetStore } from '../../stores/useAssetStore.js';
import { useToastStore } from '../../stores/useToastStore.js';
import { useTradingStore } from '../../stores/useTradingStore.js';
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
  } = useSettingsStore();

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
              className={`flex-1 text-[10px] font-black uppercase tracking-wider py-2 rounded-lg transition-all ${
                activeTab === 'telemetry' 
                  ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/20' 
                  : 'text-gray-500 hover:text-white border border-transparent'
              }`} 
              onClick={() => setActiveTab('telemetry')}
            >
              Telemetry
            </button>
            <button 
              className={`flex-1 text-[10px] font-black uppercase tracking-wider py-2 rounded-lg transition-all ${
                activeTab === 'settings' 
                  ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/20' 
                  : 'text-gray-500 hover:text-white border border-transparent'
              }`} 
              onClick={() => setActiveTab('settings')}
            >
              Controller Settings
            </button>
          </div>

          {activeTab === 'telemetry' ? (
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
            </div>
          ) : (
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

              {/* Copy Ghost Trades */}
              <div>
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
