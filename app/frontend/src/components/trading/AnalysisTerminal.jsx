/**
 * AnalysisTerminal — fixed-height terminal-style signal log.
 * Replaces the dynamic Manipulation + Confluence badge sections in OTEORing.
 * Pure CSS, zero new dependencies.
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { getManipulationLabels, getConfluenceItems } from './chartUtils.js';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function ts() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}

/**
 * Build a structured "entry" object from current signal/manipulation state.
 * This is compared to the previous entry to detect meaningful changes.
 */
function buildEntry(signal, manipulation, direction, warmup) {
  if (warmup) {
    return { type: 'warmup', key: 'warmup' };
  }

  const manipLabels = getManipulationLabels(manipulation);
  const confluenceItems = getConfluenceItems(signal, direction);
  const key = [direction ?? 'null', manipLabels.join(','), confluenceItems.join(',')].join('|');

  return { type: 'signal', key, direction, manipLabels, confluenceItems };
}

/** Convert a structured entry into an array of styled log line objects. */
function entryToLines(entry, time) {
  if (entry.type === 'warmup') {
    return [
      { text: `[${time}] ── WAITING FOR SIGNAL DATA ──────────────`, color: 'dim' },
      { text: `[${time}]  STATUS  Warming up…`, color: 'dim' },
    ];
  }

  const { direction, manipLabels, confluenceItems } = entry;
  const dirLabel = direction === 'call' ? 'CALL ▲' : direction === 'put' ? 'PUT  ▼' : 'NEUTRAL ◆';
  const dirColor = direction === 'call' ? 'call' : direction === 'put' ? 'put' : 'neutral';
  const flagClear = manipLabels.length === 0;

  const lines = [
    { text: `[${time}] ━━ SIGNAL UPDATE ━━━━━━━━━━━━━━━━━━━━━━━`, color: 'header' },
    { text: `[${time}]  DIR    ${dirLabel}`, color: dirColor },
    { text: `[${time}]  FLAGS  ${flagClear ? '✓ Clear' : '⚠ ' + manipLabels.join(', ')}`, color: flagClear ? 'ok' : 'warn' },
  ];

  if (confluenceItems.length > 0) {
    lines.push({ text: `[${time}]  ── CONFLUENCES ──`, color: 'sub' });
    confluenceItems.forEach((item) => {
      lines.push({ text: `[${time}]  ●  ${item}`, color: 'confluence' });
    });
  } else {
    lines.push({ text: `[${time}]  ── No strong confluences detected`, color: 'dim' });
  }

  return lines;
}

// ─── Color map (Tailwind inline-style fallback for monospace terminal) ─────────

const COLOR = {
  header: '#22d3ee', // cyan-400
  sub: '#64748b', // slate-500
  call: '#34d399', // emerald-400
  put: '#fe7453', // brand orange
  neutral: '#60a5fa', // blue-400
  ok: '#34d399', // emerald-400
  warn: '#fbbf24', // amber-400
  confluence: '#a5f3fc', // cyan-200
  dim: '#374151', // gray-700
  ts: '#1f2937', // gray-800 — timestamp portion
};

function getColor(color) {
  return COLOR[color] ?? '#9ca3af';
}

// ─── Sub-component: a single terminal line ─────────────────────────────────────

function TermLine({ text, color }) {
  // Dim the timestamp bracket portion, color the rest
  const bracketEnd = text.indexOf(']');
  if (bracketEnd === -1) {
    return (
      <div style={{ color: getColor(color), lineHeight: '1.6' }}>
        {text}
      </div>
    );
  }

  const tspart = text.slice(0, bracketEnd + 1);
  const rest = text.slice(bracketEnd + 1);

  return (
    <div style={{ lineHeight: '1.6' }}>
      <span style={{ color: COLOR.ts }}>{tspart}</span>
      <span style={{ color: getColor(color) }}>{rest}</span>
    </div>
  );
}

// ─── Main component ────────────────────────────────────────────────────────────

export default function AnalysisTerminal({ signal, manipulation, direction, warmup }) {
  const [lines, setLines] = useState(() => [
    { text: `[${ts()}] ── ANALYSIS TERMINAL READY ───────────────`, color: 'header' },
    { text: `[${ts()}]  Awaiting signal stream…`, color: 'dim' },
  ]);

  const prevKeyRef = useRef(null);
  const termBodyRef = useRef(null);

  // Append new log block only when data meaningfully changes
  useEffect(() => {
    const entry = buildEntry(signal, manipulation, direction, warmup);
    if (entry.key === prevKeyRef.current) return; // no change — skip
    prevKeyRef.current = entry.key;

    const newLines = entryToLines(entry, ts());
    setLines((prev) => [...prev, ...newLines]);
  }, [signal, manipulation, direction, warmup]);

  // Auto-scroll the terminal body only — never the page viewport
  useEffect(() => {
    const el = termBodyRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [lines]);

  const handleClear = useCallback(() => {
    setLines([{ text: `[${ts()}] ── TERMINAL CLEARED ──────────────────────`, color: 'header' }]);
    prevKeyRef.current = null; // force re-emit on next update
  }, []);

  return (
    <div style={{ width: '100%', marginTop: '12px' }}>
      {/* ── Header bar ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '4px',
          padding: '0 2px',
        }}
      >
        <span
          style={{
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
            fontSize: '12px',
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            color: '#22d3ee',
            opacity: 0.7,
          }}
        >
          ▸ analysis terminal
        </span>
        <button
          id="analysis-terminal-clear-btn"
          onClick={handleClear}
          style={{
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
            fontSize: '9px',
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            color: '#22d3ee',
            background: 'transparent',
            border: '1px solid rgba(34,211,238,0.2)',
            borderRadius: '3px',
            padding: '1px 8px',
            cursor: 'pointer',
            opacity: 0.7,
            transition: 'opacity 0.15s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
          onMouseLeave={(e) => (e.currentTarget.style.opacity = '0.7')}
        >
          CLEAR
        </button>
      </div>

      {/* ── Terminal body ── */}
      <div
        ref={termBodyRef}
        style={{
          position: 'relative',
          height: '330px',
          overflowY: 'auto',
          background: '#0d1117',
          borderRadius: '8px',
          border: '1px solid rgba(34,211,238,0.1)',
          boxShadow: `0 0 0 1px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.03), 0 0 20px rgba(34,211,238,0.04)`,
          padding: '10px 12px 10px 12px',
          fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
          fontSize: '14px',
          userSelect: 'text',

          // Thin custom scrollbar
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(34,211,238,0.15) transparent',
        }}
      >
        {/* Subtle scanline overlay */}
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            inset: 0,
            background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.04) 2px, rgba(0,0,0,0.04) 4px)',
            pointerEvents: 'none',
            borderRadius: '8px',
          }}
        />

        {/* Log lines */}
        {lines.map((line, i) => (
          <TermLine key={i} text={line.text} color={line.color} />
        ))}

        {/* Blinking cursor */}
        <span
          aria-hidden="true"
          style={{
            display: 'inline-block',
            color: '#22d3ee',
            animation: 'otc-blink 1.1s step-start infinite',
            marginLeft: '2px',
          }}
        >
          ▌
        </span>

      </div>

      {/* Blink keyframe — injected once via a style tag */}
      <style>{`
        @keyframes otc-blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0; }
        }
      `}</style>
    </div>
  );
}
