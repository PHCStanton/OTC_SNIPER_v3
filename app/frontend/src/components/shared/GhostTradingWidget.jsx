import { useState, useRef } from 'react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useRiskStore } from '../../stores/useRiskStore.js';
import { X, TrendingUp, TrendingDown, Target, Zap, ShieldAlert, Award } from 'lucide-react';

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
  const { ghostTradingEnabled, autoGhostEnabled, ghostWidgetPosition, setGhostWidgetPosition, ghostIcon } = useSettingsStore();
  const { ghostPnl, ghostWinRate, ghostTotalTrades, ghostMaxDrawdown } = useRiskStore();
  const [isOpen, setIsOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef({ startX: 0, startY: 0, initialX: 0, initialY: 0, isDragging: false });
  const containerRef = useRef(null);

  if (!ghostTradingEnabled && !autoGhostEnabled) return null;

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

  return (
    <div 
      ref={containerRef}
      className="absolute bottom-6 left-6 z-50"
      style={{ transform: `translate(${position.x}px, ${position.y}px)` }}
    >
      {/* The Popup */}
      {isOpen && (
        <div className="absolute bottom-16 left-0 mb-4 w-[340px] rounded-2xl border border-white/10 bg-[#0f1419]/95 p-5 shadow-2xl backdrop-blur-xl origin-bottom-left animate-in fade-in zoom-in duration-200">
          <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-3">
            <div className="flex items-center gap-2 text-[#f5df19]">
              <Zap size={18} />
              <h3 className="text-base font-bold tracking-tight text-[#e3e6e7]">Ghost Trader Stats</h3>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="rounded-full p-1 text-gray-500 hover:bg-white/10 hover:text-white transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <StatBox label="Simulated P&L" value={formatCurrency(ghostPnl)} tone={ghostPnl >= 0 ? 'emerald' : 'rose'} icon={ghostPnl >= 0 ? TrendingUp : TrendingDown} />
              <StatBox label="Win Rate" value={`${Math.round(ghostWinRate)}%`} tone="emerald" icon={Award} />
              <StatBox label="Total Trades" value={String(ghostTotalTrades)} tone="slate" icon={Target} />
              <StatBox label="Max Drawdown" value={formatCurrency(-Math.abs(ghostMaxDrawdown))} tone="rose" icon={TrendingDown} />
            </div>

            <div className="rounded-xl border border-white/5 bg-[#151a22] p-3 text-xs text-gray-400 leading-relaxed">
              <div className="flex items-start gap-2">
                <ShieldAlert size={14} className="mt-0.5 text-gray-500 shrink-0" />
                <p>
                  These stats reflect the simulated performance of the ghost trader module. 
                  Live account balances remain completely unaffected.
                </p>
              </div>
              {autoGhostEnabled && (
                <p className="mt-2 text-[10px] uppercase tracking-[0.18em] text-[#f5df19]">
                  Auto-Ghost is active on currently streamed assets
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Floating Ghost Icon */}
      <button
        onClick={handleClick}
        onPointerDown={handlePointerDown}
        className={`relative flex h-14 w-14 items-center justify-center rounded-full border-2 bg-[#1f1a00] shadow-lg shadow-[#f5df19]/20 transition-all ${isDragging ? 'cursor-grabbing scale-110 shadow-[#f5df19]/40' : 'cursor-grab hover:scale-110 hover:shadow-[#f5df19]/40'} ${isOpen ? 'border-[#f5df19]' : 'border-[#f5df19]/30'}`}
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
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#f5df19] opacity-75"></span>
            <span className="relative inline-flex h-3 w-3 rounded-full bg-[#f5df19]"></span>
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
    emerald: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-400',
    rose: 'border-red-400/20 bg-red-400/10 text-red-400',
    slate: 'border-white/5 bg-white/5 text-[#e3e6e7]',
  };

  return (
    <div className={`rounded-xl border p-3 ${toneClasses[tone]}`}>
      <div className="flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-[0.2em] opacity-70">
        {Icon && <Icon size={12} />}
        {label}
      </div>
      <div className="mt-1 text-base font-black tracking-tight">{value}</div>
    </div>
  );
}
