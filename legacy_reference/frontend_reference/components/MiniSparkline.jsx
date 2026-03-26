import React, { useMemo } from 'react';
import { TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';

const MiniSparkline = ({
  asset,
  prices = [],
  oteoScore = 50,
  action = 'CALL',
  confidence = 'LOW',
  manipulation = {},
  warmup = { ready: true, ticks: 50 },
  onClick
}) => {
  // Color configuration
  const colors = {
    HIGH: { border: 'border-cyan-400/40', bg: 'bg-cyan-400/5', text: 'text-cyan-400', line: '#00d4ff' },
    MEDIUM: { border: 'border-amber-500/30', bg: 'bg-amber-500/5', text: 'text-amber-500', line: '#ff9500' },
    LOW: { border: 'border-white/10', bg: 'bg-white/5', text: 'text-emerald-400', line: '#00ff9d' },
    WARMING: { border: 'border-amber-500/20 border-dashed', bg: 'bg-amber-500/5', text: 'text-slate-400', line: '#64748b' },
    MANIPULATION: { border: 'border-red-500/40 animate-pulse', bg: 'bg-red-500/5', text: 'text-red-500', line: '#ff3b5c' }
  };

  const isManipulated = manipulation.push_snap || manipulation.pinning;
  const isWarming = !warmup.ready;
  
  let stateKey = confidence;
  if (isWarming) stateKey = 'WARMING';
  if (isManipulated) stateKey = 'MANIPULATION';

  const theme = colors[stateKey] || colors.LOW;

  // SVG dimensions
  const width = 200;
  const height = 80;
  const padding = 10;

  const path = useMemo(() => {
    if (!prices || prices.length === 0) return '';
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const range = maxPrice - minPrice || 1;

    const points = prices.map((price, i) => {
      const x = padding + (i / Math.max(prices.length - 1, 1)) * (width - 2 * padding);
      const y = height - padding - ((price - minPrice) / range) * (height - 2 * padding);
      return `${x},${y}`;
    });

    return `M ${points.join(' L ')}`;
  }, [prices, width, height, padding]);

  return (
    <div 
      className={`relative w-full h-[120px] rounded-lg cursor-pointer transition-all hover:scale-[1.02] active:scale-95 ${theme.bg} ${theme.border} border`}
      onClick={() => onClick && onClick(asset)}
    >
      {/* Header */}
      <div className="absolute top-2 left-2 right-2 flex justify-between items-center z-10">
        <span className="font-bold text-xs text-white">{asset}</span>
        {isManipulated && <AlertTriangle className="w-3 h-3 text-red-500" />}
        {isWarming && <span className="text-[9px] text-amber-500">{warmup.ticks}/50</span>}
      </div>

      {/* SVG Sparkline */}
      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} className="absolute inset-0" preserveAspectRatio="none">
        <path
          d={path}
          fill="none"
          stroke={theme.line}
          strokeWidth="1.5"
          vectorEffect="non-scaling-stroke"
        />
      </svg>

      {/* Footer / OTEO Score */}
      <div className="absolute bottom-2 left-2 right-2 flex justify-between items-end z-10">
        <div className={`text-xl font-black ${theme.text}`}>
          {oteoScore.toFixed(1)}
        </div>
        <div className={`flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-black/40 ${action === 'CALL' ? 'text-green-400' : 'text-red-400'}`}>
          {action === 'CALL' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {action}
        </div>
      </div>
    </div>
  );
};

export default MiniSparkline;
