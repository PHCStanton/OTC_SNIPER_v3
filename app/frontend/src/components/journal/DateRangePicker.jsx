import React, { useState, useRef, useEffect } from 'react';
import { ChevronLeft, ChevronRight, CalendarDays, X } from 'lucide-react';

const MONTH_NAMES = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December'
];
const DAY_LABELS = ['Su','Mo','Tu','We','Th','Fr','Sa'];

function buildCalendarDays(year, month) {
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  return cells;
}

function toIso(year, month, day) {
  return `${year}-${String(month + 1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
}

function isoToMs(iso) {
  if (!iso) return null;
  return new Date(iso + 'T00:00:00Z').getTime();
}

export default function DateRangePicker({ dateFrom, dateTo, onChange }) {
  const now = new Date();
  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState(now.getFullYear());
  const [viewMonth, setViewMonth] = useState(now.getMonth());
  const [hoverDate, setHoverDate] = useState(null);
  const popoverRef = useRef(null);

  useEffect(() => {
    const handle = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setOpen(false);
        setHoverDate(null);
      }
    };
    if (open) document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [open]);

  const fromMs = isoToMs(dateFrom);
  const toMs   = isoToMs(dateTo);

  const handleDayClick = (year, month, day) => {
    const iso = toIso(year, month, day);
    const ms  = isoToMs(iso);
    if (!dateFrom) {
      onChange({ from: iso, to: null });
    } else if (!dateTo) {
      if (ms < fromMs) {
        onChange({ from: iso, to: dateFrom });
      } else {
        onChange({ from: dateFrom, to: iso });
      }
      setOpen(false);
      setHoverDate(null);
    } else {
      onChange({ from: iso, to: null });
    }
  };

  const getDayState = (year, month, day) => {
    const iso = toIso(year, month, day);
    const ms  = isoToMs(iso);
    const isFrom = iso === dateFrom;
    const isTo   = iso === dateTo;
    let rangeStart = fromMs;
    let rangeEnd   = toMs;
    if (dateFrom && !dateTo && hoverDate) {
      const hMs = isoToMs(hoverDate);
      rangeStart = Math.min(fromMs, hMs);
      rangeEnd   = Math.max(fromMs, hMs);
    }
    const inRange = rangeStart && rangeEnd && ms > rangeStart && ms < rangeEnd;
    const isEdge  = isFrom || isTo;
    return { isFrom, isTo, inRange, isEdge };
  };

  const prevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1); }
    else setViewMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1); }
    else setViewMonth(m => m + 1);
  };

  const clear = () => { onChange({ from: null, to: null }); setOpen(false); setHoverDate(null); };

  const label = () => {
    if (!dateFrom && !dateTo) return 'All Data';
    if (dateFrom && !dateTo) return `From ${dateFrom}`;
    if (dateFrom === dateTo) return dateFrom;
    return `${dateFrom} \u2192 ${dateTo}`;
  };

  const cells = buildCalendarDays(viewYear, viewMonth);

  return (
    <div className="relative" ref={popoverRef}>
      <button
        onClick={() => setOpen(o => !o)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono transition-all ${dateFrom ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-300 hover:border-cyan-400' : 'bg-[#21242c] border-white/5 text-gray-300 hover:text-white hover:bg-[#2d3139]'}`}
        title="Filter by date or date range"
      >
        <CalendarDays size={13} className={dateFrom ? 'text-cyan-400' : 'text-gray-400'} />
        <span className="max-w-[180px] truncate">{label()}</span>
        {(dateFrom || dateTo) && (
          <span onClick={(e) => { e.stopPropagation(); clear(); }} className="ml-1 text-gray-500 hover:text-rose-400 transition-colors cursor-pointer" title="Clear">
            <X size={11} />
          </span>
        )}
      </button>

      {open && (
        <div className="absolute top-full mt-2 left-0 z-50 w-[280px] bg-[#1a1d26] border border-white/10 rounded-xl shadow-2xl shadow-black/60 p-3">
          <div className="flex items-center justify-between mb-2.5 px-1">
            <button onClick={prevMonth} className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-all">
              <ChevronLeft size={14} />
            </button>
            <span className="text-xs font-black uppercase tracking-wider text-white">
              {MONTH_NAMES[viewMonth]} {viewYear}
            </span>
            <button onClick={nextMonth} className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-all">
              <ChevronRight size={14} />
            </button>
          </div>

          <div className="grid grid-cols-7 mb-1">
            {DAY_LABELS.map(d => (
              <div key={d} className="text-center text-[9px] font-bold text-gray-500 pb-1">{d}</div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-y-0.5">
            {cells.map((day, idx) => {
              if (!day) return <div key={`e-${idx}`} />;
              const { isFrom, isTo, inRange, isEdge } = getDayState(viewYear, viewMonth, day);
              const isoDay = toIso(viewYear, viewMonth, day);
              return (
                <button
                  key={isoDay}
                  onClick={() => handleDayClick(viewYear, viewMonth, day)}
                  onMouseEnter={() => dateFrom && !dateTo && setHoverDate(isoDay)}
                  onMouseLeave={() => setHoverDate(null)}
                  className={`relative h-8 w-full text-[11px] font-mono rounded-lg transition-all ${isEdge ? 'bg-cyan-500 text-black font-black shadow-md shadow-cyan-500/40' : inRange ? 'bg-cyan-500/15 text-cyan-300' : 'text-gray-300 hover:bg-white/5 hover:text-white'}`}
                >
                  {day}
                  {isFrom && !dateTo && (
                    <span className="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-amber-400" />
                  )}
                </button>
              );
            })}
          </div>

          <div className="mt-2.5 pt-2 border-t border-white/5 flex items-center justify-between">
            <p className="text-[9px] text-gray-500 font-mono">
              {!dateFrom ? 'Click to set start date' : !dateTo ? 'Click to set end date' : `${dateFrom} \u2192 ${dateTo}`}
            </p>
            {(dateFrom || dateTo) && (
              <button onClick={clear} className="text-[9px] font-bold uppercase tracking-wide text-rose-400 hover:text-rose-300 transition-colors">
                Clear
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
