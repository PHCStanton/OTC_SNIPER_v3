import React from 'react';
import { LineChart } from 'lucide-react';

export default function EquityCurve({ ghostTrades }) {
  // Simple SVG line chart for cumulative PnL
  let cumulativePnl = 0;
  const dataPoints = ghostTrades.map((t, i) => {
    cumulativePnl += (t.pnl || 0);
    return { x: i, y: cumulativePnl };
  });

  // Always start at 0
  dataPoints.unshift({ x: -1, y: 0 });

  const minPnl = Math.min(...dataPoints.map(d => d.y), 0);
  const maxPnl = Math.max(...dataPoints.map(d => d.y), 0);
  
  const width = 600;
  const height = 150;
  const padding = 20;

  const getCoordinates = (point) => {
    const xRange = Math.max(dataPoints.length - 1, 1);
    const yRange = maxPnl - minPnl || 1;
    
    const x = padding + ((point.x + 1) / xRange) * (width - 2 * padding);
    const y = height - padding - ((point.y - minPnl) / yRange) * (height - 2 * padding);
    return `${x},${y}`;
  };

  const pointsStr = dataPoints.map(getCoordinates).join(' L ');
  const zeroLineY = height - padding - ((0 - minPnl) / (maxPnl - minPnl || 1)) * (height - 2 * padding);

  return (
    <div className="bg-[#141818] border border-white/5 rounded-xl p-5 lg:col-span-2">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-bold text-gray-400 flex items-center gap-2 uppercase tracking-wider">
          <LineChart size={16} className="text-[#f5df19]" />
          Equity Curve
        </h3>
        <span className="text-[10px] font-bold text-gray-500 bg-white/5 px-2 py-0.5 rounded-full">
          Current Session PnL
        </span>
      </div>
      
      {ghostTrades.length === 0 ? (
        <div className="h-[150px] flex items-center justify-center text-gray-600 italic text-xs">
          Not enough data to plot equity curve.
        </div>
      ) : (
        <div className="relative w-full overflow-hidden">
          <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full drop-shadow-lg">
            {/* Zero Line */}
            <line 
              x1={padding} 
              y1={zeroLineY} 
              x2={width - padding} 
              y2={zeroLineY} 
              stroke="rgba(255,255,255,0.1)" 
              strokeWidth="1" 
              strokeDasharray="4 4" 
            />
            
            {/* Equity Line */}
            <path 
              d={`M ${pointsStr}`} 
              fill="none" 
              stroke={cumulativePnl >= 0 ? "#10b981" : "#f43f5e"} 
              strokeWidth="2" 
              strokeLinecap="round" 
              strokeLinejoin="round" 
            />

            {/* Gradient Fill under curve */}
            <path 
              d={`M ${padding},${zeroLineY} L ${pointsStr} L ${width - padding},${zeroLineY} Z`} 
              fill={cumulativePnl >= 0 ? "rgba(16, 185, 129, 0.1)" : "rgba(244, 63, 94, 0.1)"} 
            />
          </svg>
        </div>
      )}
    </div>
  );
}