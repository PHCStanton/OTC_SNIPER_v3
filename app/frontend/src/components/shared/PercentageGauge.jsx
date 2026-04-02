import React, { useEffect, useState } from 'react';

export default function PercentageGauge({ 
  percentage = 0, 
  size = 120, 
  strokeWidth = 10, 
  color = '#f5df19',
  trackColor = 'rgba(255,255,255,0.05)',
  label = 'Win Rate',
  animated = true
}) {
  const [displayPercentage, setDisplayPercentage] = useState(animated ? 0 : percentage);

  useEffect(() => {
    if (animated) {
      const timeout = setTimeout(() => {
        setDisplayPercentage(percentage);
      }, 100);
      return () => clearTimeout(timeout);
    } else {
      setDisplayPercentage(percentage);
    }
  }, [percentage, animated]);

  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  // Cap at 100%
  const safePercentage = Math.min(100, Math.max(0, displayPercentage));
  const offset = circumference - (safePercentage / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={trackColor}
            strokeWidth={strokeWidth}
            fill="none"
          />
          {/* Progress arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={color}
            strokeWidth={strokeWidth}
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center flex-col">
          <span className="text-xl font-bold text-white drop-shadow-md">
            {Math.round(displayPercentage)}%
          </span>
        </div>
      </div>
      {label && <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">{label}</span>}
    </div>
  );
}