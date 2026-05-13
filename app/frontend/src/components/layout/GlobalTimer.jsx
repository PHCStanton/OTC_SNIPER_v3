import React, { useState, useEffect, useRef } from 'react';
import { Clock, Timer, Play, Square, RotateCcw, Bell, BellRing } from 'lucide-react';
import { soundManager } from '../../utils/soundUtils.js';

export default function GlobalTimer() {
  const [mode, setMode] = useState('utc'); // 'utc' | 'stopwatch'
  const [isRunning, setIsRunning] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [utcTime, setUtcTime] = useState(new Date());
  
  // Stopwatch refs
  const startTimeRef = useRef(0);
  const timerIntervalRef = useRef(null);
  
  // Alert state
  const [alertTime, setAlertTime] = useState(''); // Custom minutes
  const [activeAlertMinutes, setActiveAlertMinutes] = useState(null);
  const [alertTriggered, setAlertTriggered] = useState(false);

  // UTC Clock update
  useEffect(() => {
    const interval = setInterval(() => {
      setUtcTime(new Date());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Stopwatch Logic
  const startStopwatch = () => {
    if (isRunning) return;
    setIsRunning(true);
    startTimeRef.current = Date.now() - elapsedTime;
    timerIntervalRef.current = setInterval(() => {
      setElapsedTime(Date.now() - startTimeRef.current);
    }, 10);
  };

  const stopStopwatch = () => {
    if (!isRunning) return;
    setIsRunning(false);
    clearInterval(timerIntervalRef.current);
  };

  const resetStopwatch = () => {
    stopStopwatch();
    setElapsedTime(0);
    setAlertTriggered(false);
  };

  // Alert Checking
  useEffect(() => {
    if (activeAlertMinutes && isRunning) {
      const alertMs = activeAlertMinutes * 60 * 1000;
      if (elapsedTime >= alertMs && !alertTriggered) {
        setAlertTriggered(true);
        soundManager.playTimerAlert();
      }
    }
  }, [elapsedTime, activeAlertMinutes, isRunning, alertTriggered]);

  const formatStopwatch = (ms) => {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const seconds = (totalSeconds % 60).toString().padStart(2, '0');
    const centiseconds = Math.floor((ms % 1000) / 10).toString().padStart(2, '0');
    return `${minutes}:${seconds}.${centiseconds}`;
  };

  const formatUTC = (date) => {
    return date.toUTCString().split(' ')[4]; // HH:mm:ss
  };

  return (
    <div className="flex h-12 w-full items-center justify-between border-t border-white/5 bg-[#0b0f13] px-6 shadow-[0_-4px_20px_rgba(0,0,0,0.4)] transition-all">
      {/* Left: Mode Switchers */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setMode('utc')}
          className={`flex h-8 items-center gap-2 rounded-lg px-3 text-[10px] font-black uppercase tracking-widest transition-all ${
            mode === 'utc' ? 'bg-[#f5df19]/10 text-[#f5df19] shadow-[inset_0_0_10px_rgba(245,223,25,0.1)]' : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          <Clock size={14} />
          UTC Clock
        </button>
        <button
          onClick={() => setMode('stopwatch')}
          className={`flex h-8 items-center gap-2 rounded-lg px-3 text-[10px] font-black uppercase tracking-widest transition-all ${
            mode === 'stopwatch' ? 'bg-emerald-500/10 text-emerald-400 shadow-[inset_0_0_10px_rgba(16,185,129,0.1)]' : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          <Timer size={14} />
          Stopwatch
        </button>
      </div>

      {/* Center: Main Display */}
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-4">
          <span className={`font-mono text-xl font-black tracking-tighter ${mode === 'utc' ? 'text-[#f5df19]' : 'text-emerald-400'}`}>
            {mode === 'utc' ? formatUTC(utcTime) : formatStopwatch(elapsedTime)}
          </span>
          
          {mode === 'stopwatch' && (
            <div className="flex items-center gap-1.5">
              {!isRunning ? (
                <button onClick={startStopwatch} className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500 text-black shadow-lg shadow-emerald-500/20 hover:scale-110 active:scale-95 transition-all">
                  <Play size={12} fill="currentColor" />
                </button>
              ) : (
                <button onClick={stopStopwatch} className="flex h-7 w-7 items-center justify-center rounded-full bg-rose-500 text-white shadow-lg shadow-rose-500/20 hover:scale-110 active:scale-95 transition-all">
                  <Square size={12} fill="currentColor" />
                </button>
              )}
              <button onClick={resetStopwatch} className="flex h-7 w-7 items-center justify-center rounded-full bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white transition-all">
                <RotateCcw size={12} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Right: Alerts & Presets */}
      <div className="flex items-center gap-4">
        {mode === 'stopwatch' && (
          <>
            <div className="flex items-center gap-1 rounded-lg bg-white/5 p-0.5">
              {[5, 10, 15].map((m) => (
                <button
                  key={m}
                  onClick={() => {
                    setActiveAlertMinutes(m);
                    setAlertTriggered(false);
                  }}
                  className={`rounded-md px-2 py-1 text-[9px] font-black tracking-widest transition-all ${
                    activeAlertMinutes === m ? 'bg-[#f5df19] text-black shadow-lg' : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  {m}M
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <input
                type="number"
                placeholder="MIN"
                value={alertTime}
                onChange={(e) => setAlertTime(e.target.value)}
                className="h-7 w-12 rounded-lg bg-white/5 px-2 text-center text-[10px] font-black text-white outline-none focus:bg-white/10"
              />
              <button
                onClick={() => {
                  const m = parseFloat(alertTime);
                  if (m > 0) {
                    setActiveAlertMinutes(m);
                    setAlertTriggered(false);
                  }
                }}
                className="flex h-7 items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-3 text-[9px] font-black uppercase tracking-widest text-gray-400 hover:bg-white/10 hover:text-white transition-all"
              >
                {activeAlertMinutes && !alertTriggered ? <BellRing size={12} className="text-[#f5df19] animate-pulse" /> : <Bell size={12} />}
                SET ALERT
              </button>
              
              {(activeAlertMinutes || alertTriggered) && (
                <button 
                  onClick={() => {
                    setActiveAlertMinutes(null);
                    setAlertTriggered(false);
                  }}
                  className="text-[9px] font-bold text-rose-500 hover:underline"
                >
                  CLEAR
                </button>
              )}
            </div>
          </>
        )}
        
        {mode === 'utc' && (
          <div className="flex items-center gap-2 text-[9px] font-black uppercase tracking-[0.2em] text-gray-600">
            <Clock size={12} />
            Network Sync Active
          </div>
        )}
      </div>
    </div>
  );
}
