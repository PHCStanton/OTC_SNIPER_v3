/**
 * OTEORing — circular confidence indicator used in the Phase 5 trading workspace.
 */
import { ArrowDownRight, ArrowUpRight } from 'lucide-react';
import { formatAssetLabel, getSignalConfidence, getSignalDirection, getSignalLabel } from './chartUtils.js';

export default function OTEORing({ asset, signal, warmup = false }) {
  const confidence = warmup ? 0 : getSignalConfidence(signal);
  const direction = getSignalDirection(signal);
  const label = getSignalLabel(signal);

  // Math for a large, crisp circle
  const size = 300;
  const strokeWidth = 24;
  const center = size / 2;
  const radius = center - strokeWidth;
  const circumference = 2 * Math.PI * radius;
  // Calculate offset. We leave a small gap at the bottom for aesthetics (like in the screenshot)
  // Let's say the arc covers 85% of the circle, so there's a 15% gap at the bottom.
  // 15% of circumference is the gap. 
  const arcLength = 0.85 * circumference;
  const gapLength = circumference - arcLength;
  
  // We want the ring to start after the gap. 
  // SVG circles start at 3 o'clock. We rotate it by 90deg to start at 6 o'clock.
  // If we rotate it by 90deg, 0 is at bottom (6 o'clock). 
  // We want a gap centered at the bottom. So the gap is from -7.5% to +7.5% (around bottom).
  // This means the arc starts at +7.5% and ends at -7.5%.
  
  // To keep it simple and perfectly match standard circular progress bars:
  // We will just draw the whole circumference but use strokeDasharray to leave the gap.
  // We map the confidence (0-100) to the arcLength (0 to 85% of circumference).
  
  const fillLength = (confidence / 100) * arcLength;
  // Dasharray format: [dash, gap]
  // We want the dash to be `fillLength`, and the gap to be the rest of the circumference.
  
  const isPut = direction === 'put';
  const isCall = direction === 'call';

  const glowColor = warmup
    ? 'rgba(100,116,139,0.2)'
    : isPut
      ? 'rgba(254,116,83,0.4)'
      : 'rgba(16,185,129,0.4)';

  const accentClass = warmup
    ? 'text-slate-400'
    : isPut
      ? 'text-[#fe7453]'
      : 'text-emerald-500';

  // Rotation: We want the gap at the bottom. 
  // Default start is 3 o'clock. We want it to start at roughly 7 o'clock.
  // 7 o'clock is 120 degrees from 3 o'clock (clockwise). 
  // Let's rotate by 115 degrees.
  const rotation = 117;

  return (
    <div className="flex h-full flex-col items-center justify-center py-4">
      {/* Container for SVG */}
      <div className="relative flex h-64 w-64 items-center justify-center sm:h-72 sm:w-72">
        <svg 
          className="h-full w-full" 
          viewBox={`0 0 ${size} ${size}`}
          style={{ 
            filter: `drop-shadow(0 0 10px ${glowColor}) drop-shadow(0 0 20px ${glowColor})`,
            transform: `rotate(${rotation}deg)` 
          }}
        >
          <defs>
            <linearGradient id="putGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fe7453" />
              <stop offset="100%" stopColor="#f5df19" />
            </linearGradient>
            <linearGradient id="callGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#34d399" />
            </linearGradient>
            <linearGradient id="warmupGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#475569" />
              <stop offset="100%" stopColor="#64748b" />
            </linearGradient>
          </defs>

          {/* Background track (shows the full 85% arc) */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="transparent"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${gapLength}`}
            strokeLinecap="round"
            className="text-white/5"
          />

          {/* Progress ring */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="transparent"
            stroke={warmup ? 'url(#warmupGradient)' : isPut ? 'url(#putGradient)' : 'url(#callGradient)'}
            strokeWidth={strokeWidth}
            strokeDasharray={`${fillLength} ${circumference}`}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        {/* Center content (un-rotated) */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-5xl sm:text-7xl font-black tracking-tighter ${accentClass}`}>
            {warmup ? '—' : `${Math.round(confidence)}%`}
          </span>
          <span className="mt-2 text-xs font-bold uppercase tracking-[0.2em] text-gray-500">
            {warmup ? 'Warming up' : isPut ? 'Sell Pressure' : isCall ? 'Buy Pressure' : 'Neutral'}
          </span>
        </div>
      </div>

      {/* Label / Direction Badge */}
      {!warmup && (
        <div className="mt-6 flex items-center gap-2 rounded-full border border-white/5 bg-[#1a1717]/80 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.15em] text-gray-300 shadow-lg backdrop-blur">
          {isPut ? (
            <ArrowDownRight size={14} className="text-[#fe7453]" />
          ) : (
            <ArrowUpRight size={14} className="text-emerald-400" />
          )}
          <span>{label}</span>
        </div>
      )}
    </div>
  );
}
