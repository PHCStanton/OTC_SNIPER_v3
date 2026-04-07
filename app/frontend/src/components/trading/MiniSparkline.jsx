/**
 * MiniSparkline — compact sparkline used in multi-chart cards.
 */
import { useMemo } from 'react';
import { buildChartPoints, extractNumericSeries, getTrendPercent, pointsToPath } from './chartUtils.js';

export default function MiniSparkline({ ticks, className = '' }) {
  const series = useMemo(() => extractNumericSeries(ticks), [ticks]);
  const points = useMemo(() => buildChartPoints(series, 240, 64, 8), [series]);
  const path = useMemo(() => pointsToPath(points), [points]);
  const trend = getTrendPercent(series);
  const positive = trend >= 0;

  if (series.length === 0) {
    return (
      <div className={`flex h-16 items-center justify-center rounded-xl border border-dashed border-white/10 bg-[#1a1717] text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500 ${className}`}>
        No data
      </div>
    );
  }

  return (
    <div className={`relative h-16 overflow-hidden rounded-xl border border-white/5 bg-[#1a1717] ${className}`}>
      <svg className="h-full w-full" viewBox="0 0 240 64" aria-hidden="true">
        <defs>
          <linearGradient id="miniSparklineLine" x1="0%" x2="100%" y1="0%" y2="0%">
            <stop offset="0%" stopColor={positive ? '#ffed6d' : '#fe7453'} />
            <stop offset="100%" stopColor="#f2892c" />
          </linearGradient>
        </defs>
        <path d="M 0 56 L 240 56 L 240 64 L 0 64 Z" fill="rgba(15,23,42,0.04)" />
        {path && <path d={path} fill="none" stroke="url(#miniSparklineLine)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />}
        
        {/* Only render the latest point as a circle to reduce DOM overhead */}
        {points.length > 0 && (
          <circle
            cx={points[points.length - 1].x}
            cy={points[points.length - 1].y}
            r={3.25}
            fill={positive ? '#ffed6d' : '#fe7453'}
          />
        )}
      </svg>
    </div>
  );
}
