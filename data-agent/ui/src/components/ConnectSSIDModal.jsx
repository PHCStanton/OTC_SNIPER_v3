import React, { useState, useEffect, useRef } from 'react';
import { X, Wifi, WifiOff, Loader2, KeyRound, CheckCircle2, AlertCircle, Ghost, DollarSign } from 'lucide-react';

export default function ConnectSSIDModal({ isOpen, onClose, telemetry, onSessionUpdated }) {
  const [ssidInput, setSsidInput] = useState('');
  const [isDemo, setIsDemo] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const overlayRef = useRef(null);

  const collector = telemetry?.collector || {};
  const isConnected = Boolean(collector.connected);
  const isConfigured = Boolean(collector.ssid_configured);

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose();
    }
    if (isOpen) {
      window.addEventListener('keydown', onKey);
    }
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleConnect = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);

    const token = ssidInput.trim();
    if (!token) {
      setErrorMsg('Please paste a valid PO SSID token string.');
      return;
    }

    setIsConnecting(true);
    try {
      const res = await fetch('/api/v1/auth/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ssid: token, is_demo: isDemo }),
      });
      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        setSuccessMsg('Session connected successfully! WebSocket reconnecting...');
        setSsidInput('');
        if (onSessionUpdated) onSessionUpdated();
        setTimeout(() => {
          onClose();
        }, 1200);
      } else {
        setErrorMsg(data.message || 'Failed to connect SSID session.');
      }
    } catch (err) {
      setErrorMsg('Unable to reach telemetry API server: ' + err.message);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    setIsConnecting(true);
    setErrorMsg(null);
    try {
      const res = await fetch('/api/v1/auth/disconnect', { method: 'POST' });
      if (res.ok) {
        setSuccessMsg('Session disconnected.');
        if (onSessionUpdated) onSessionUpdated();
        setTimeout(() => onClose(), 800);
      }
    } catch (err) {
      setErrorMsg('Error disconnecting session: ' + err.message);
    } finally {
      setIsConnecting(false);
    }
  };

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
    >
      <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden font-sans">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isConnected ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-800 text-slate-400'}`}>
              {isConnected ? <Wifi size={18} /> : <WifiOff size={18} />}
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Pocket Option Session Credentials</h2>
              <p className="text-xs text-slate-400 font-mono">Live WebSocket Streaming Authentication</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {/* Active Connection Banner */}
          <div className={`p-4 rounded-xl border flex items-center justify-between font-mono text-xs ${
            isConnected
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : isConfigured
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                : 'bg-slate-800/60 border-slate-700/60 text-slate-400'
          }`}>
            <div className="flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              <span className="font-bold">
                {isConnected ? 'Session Connected & Streaming' : isConfigured ? 'Connecting / Standby' : 'No SSID Session Configured'}
              </span>
            </div>
            <span className="text-[10px] uppercase font-semibold bg-slate-900/80 px-2.5 py-1 rounded border border-slate-800">
              {collector.is_demo ? 'Demo Mode' : 'Real Account'}
            </span>
          </div>

          {/* Account Type Toggle */}
          <div>
            <label className="text-xs font-semibold uppercase text-slate-400 block mb-2 font-mono">Account Mode</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setIsDemo(true)}
                className={`py-2 px-3 rounded-lg text-xs font-bold font-mono border flex items-center justify-center gap-2 transition ${
                  isDemo
                    ? 'bg-amber-500/20 border-amber-500/60 text-amber-300'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                <Ghost size={14} />
                Demo Account
              </button>

              <button
                type="button"
                onClick={() => setIsDemo(false)}
                className={`py-2 px-3 rounded-lg text-xs font-bold font-mono border flex items-center justify-center gap-2 transition ${
                  !isDemo
                    ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-300'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                <DollarSign size={14} />
                Real Account
              </button>
            </div>
          </div>

          {/* SSID Input */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-slate-400 block font-mono flex items-center gap-1.5">
              <KeyRound size={14} className="text-cyan-400" />
              PO Session SSID Frame
            </label>
            <textarea
              rows={3}
              value={ssidInput}
              onChange={(e) => {
                const val = e.target.value;
                setSsidInput(val);
                // Auto-detect isDemo from JSON payload if present
                if (val.includes('"isDemo":0') || val.includes('"isDemo": 0') || val.includes("'isDemo': 0") || val.includes("'isDemo':0")) {
                  setIsDemo(false);
                } else if (val.includes('"isDemo":1') || val.includes('"isDemo": 1') || val.includes("'isDemo': 1") || val.includes("'isDemo':1")) {
                  setIsDemo(true);
                }
              }}
              placeholder={'42["auth",{"session":"YOUR_SESSION_SSID_HERE","isDemo":1}]'}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 resize-none"
            />
            <p className="text-[10px] text-slate-500 font-mono">
              Extract from Chrome DevTools &rarr; Network &rarr; WS tab after logging into Pocket Option.
            </p>
          </div>

          {/* Messages */}
          {errorMsg && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center gap-2 text-rose-300 text-xs font-mono">
              <AlertCircle size={16} className="shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center gap-2 text-emerald-300 text-xs font-mono">
              <CheckCircle2 size={16} className="shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-3 pt-2">
            {isConnected && (
              <button
                type="button"
                onClick={handleDisconnect}
                disabled={isConnecting}
                className="px-4 py-2.5 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-300 rounded-xl font-mono text-xs font-bold transition disabled:opacity-50"
              >
                Disconnect
              </button>
            )}

            <button
              type="button"
              onClick={handleConnect}
              disabled={isConnecting}
              className="flex-1 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 rounded-xl font-mono text-xs font-bold transition flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg shadow-cyan-500/20"
            >
              {isConnecting ? <Loader2 size={14} className="animate-spin" /> : <Wifi size={14} />}
              {isConnecting ? 'Connecting Stream...' : 'Save & Connect Session'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
