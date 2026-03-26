import React, { useMemo } from 'react';

// ── Optimizer: Module-level constants (never recreated on re-render) ──────────
// Chart geometry
const W           = 420;
const H           = 140;
const PAD         = 10;
const CHART_END   = 305;   // Right edge of price chart — leaves room for OTEO ring
const CHART_W     = CHART_END - PAD;
const CHART_H     = H - PAD * 2;
// OTEO ring
const RING_RADIUS = 38;
const RING_CIRC   = 2 * Math.PI * RING_RADIUS;

/**
 * Premium Sparkline — OTC SNIPER
 *
 * Props:
 *   prices       {number[]} — recent tick prices
 *   oteoScore    {number}   — 0–100 OTEO ring score
 *   action       {string}   — 'CALL' | 'PUT'
 *   manipulation {object}   — { push_snap?: boolean, pinning?: boolean }
 */
const Sparkline = ({ prices = [], oteoScore = 0, action = 'CALL', manipulation = {} }) => {
  const lastPrice = prices.length > 0 ? prices[prices.length - 1] : null;

  // ── Price path with adaptive scaling ──────────────────────────────
  // Optimizer: uses module-level CHART_W / CHART_H constants
  const { points, lastX, lastY } = useMemo(() => {
    if (prices.length === 0) return { points: '', lastX: 0, lastY: H / 2 };
    const recent = prices.slice(-80);
    const min = Math.min(...recent);
    const max = Math.max(...recent);
    const range = max - min || 0.0001;
    const pts = recent.map((p, i) => ({
      x: PAD + (i / (recent.length - 1 || 1)) * CHART_W,
      y: PAD + CHART_H - ((p - min) / range) * CHART_H,
    }));
    const last = pts[pts.length - 1] || { x: 0, y: H / 2 };
    return { points: pts.map(p => `${p.x},${p.y}`).join(' '), lastX: last.x, lastY: last.y };
  }, [prices]);

  // ── Fill path (area beneath the line, closed to bottom) ───────────
  // FIX-5: Same coordinate system as points useMemo.
  // Optimizer: dep array is [points] only — prices is already covered by points.
  const fillPath = useMemo(() => {
    if (!points) return '';
    const recent = prices.slice(-80);
    if (recent.length < 2) return '';
    const min = Math.min(...recent);
    const max = Math.max(...recent);
    const range = max - min || 0.0001;
    const ptsStr = recent.map((p, i) =>
      `${PAD + (i / (recent.length - 1)) * CHART_W},${PAD + CHART_H - ((p - min) / range) * CHART_H}`
    ).join(' ');
    return `M ${PAD},${H} ${ptsStr} ${PAD + CHART_W},${H} Z`;
  }, [points]);

  // ── OTEO ring ─────────────────────────────────────────────────────
  // Optimizer: uses module-level RING_RADIUS / RING_CIRC constants
  const dashOffset  = RING_CIRC - (oteoScore / 100 * RING_CIRC);
  const isHighScore = oteoScore >= 75;
  const ringColor   = isHighScore ? '#00d4ff' : '#ff9500';
  const scoreColor  = action === 'CALL' ? '#00ff9d' : '#ff3b5c';

  // ── Manipulation flags ────────────────────────────────────────────
  const hasManip = manipulation.push_snap || manipulation.pinning;
  const manipLabel = manipulation.push_snap
    ? 'PUSH/SNAP'
    : manipulation.pinning
    ? 'PINNING'
    : '';

  return (
    <div className="relative w-full h-full flex items-center justify-center bg-[#060914] rounded-lg overflow-hidden"
         style={{ boxShadow: 'inset 0 0 40px rgba(0,0,0,0.6)' }}>

      {/* ── Subtle grid lines ─── */}
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
           className="absolute inset-0 w-full h-full" aria-hidden="true">
        {[0.25, 0.5, 0.75].map(f => (
          <line key={f}
            x1={0} y1={PAD + CHART_H * f}
            x2={CHART_END} y2={PAD + CHART_H * f}
            stroke="rgba(255,255,255,0.04)" strokeWidth={1} strokeDasharray="4 6" />
        ))}
      </svg>

      {/* ── Main SVG ─── */}
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="w-full h-full p-2">
        <defs>
          {/* Area fill gradient */}
          <linearGradient id="spark-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#00ff9d" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#00ff9d" stopOpacity="0" />
          </linearGradient>

          {/* OTEO ring glow filter */}
          <filter id="ring-glow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

        </defs>

        {/* Area fill */}
        {fillPath && (
          <path d={fillPath} fill="url(#spark-fill)" />
        )}

        {/* Price line */}
        {points && (
          <polyline
            points={points}
            fill="none"
            stroke="#00ff9d"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ filter: 'drop-shadow(0 0 4px rgba(0, 255, 157, 0.8))' }}
          />
        )}

        {/* Live price dot — pulsing at the last data point */}
        {lastPrice !== null && (
          <>
            {/* Outer pulse ring */}
            <circle cx={lastX} cy={lastY} r={7}
              fill="none" stroke="#00d4ff" strokeWidth={1} opacity={0.3}
              className="animate-ping" style={{ transformOrigin: `${lastX}px ${lastY}px` }}
            />
            {/* Inner dot */}
            <circle cx={lastX} cy={lastY} r={3}
              fill="#00d4ff"
              style={{ filter: 'drop-shadow(0 0 4px rgba(0, 212, 255, 0.8))' }}
            />
          </>
        )}

        {/* OTEO ring track */}
        <circle cx={380} cy={70} r={RING_RADIUS}
          fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={6} />

        {/* OTEO ring fill */}
        <circle cx={380} cy={70} r={RING_RADIUS}
          fill="none"
          stroke={ringColor}
          strokeWidth={6}
          strokeDasharray={RING_CIRC}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          filter={isHighScore ? 'url(#ring-glow)' : undefined}
          transform="rotate(-90 380 70)"
          className="transition-all duration-500 ease-out"
        />

        {/* OTEO score number */}
        <text x={380} y={76}
          textAnchor="middle"
          fill="#ffffff"
          fontSize={22}
          fontWeight="bold"
          fontFamily="monospace"
        >
          {Math.round(oteoScore).toString().padStart(2, '0')}
        </text>

        {/* Action label under score */}
        <text x={380} y={92}
          textAnchor="middle"
          fill={ringColor}
          fontSize={9}
          fontWeight="bold"
          letterSpacing={1}
          opacity={0.7}
        >
          {action}
        </text>

        {/* Stream direction badge (top-left) */}
        <text x={PAD + 2} y={PAD + 12}
          fill={scoreColor}
          fontSize={9}
          fontWeight="bold"
          letterSpacing={1}
          opacity={0.5}
        >
          {action}
        </text>

        {/* Last price display (top-right of chart, left of ring) */}
        {lastPrice !== null && (
          <text x={CHART_END - 4} y={PAD + 12}
            textAnchor="end"
            fill="rgba(255,255,255,0.5)"
            fontSize={9}
            fontFamily="monospace"
          >
            {lastPrice.toFixed(4)}
          </text>
        )}
      </svg>

      {/* ── Manipulation warning overlay ─── */}
      {hasManip && (
        <div className="absolute top-2 left-3 flex items-center gap-1 danger-flash">
          <span className="w-1.5 h-1.5 rounded-full bg-signal inline-block" />
          <span className="text-[9px] font-bold text-signal tracking-widest uppercase">
            {manipLabel}
          </span>
        </div>
      )}

      {/* ── Left gradient fade for visual depth ─── */}
      <div className="absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-[#060914] to-transparent pointer-events-none" />
    </div>
  );
};

export default Sparkline;
