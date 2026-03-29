/**
 * ConnectDialog — modal for SSID connect/disconnect.
 * Opened from TopBar session badge.
 */
import { useRef, useEffect } from 'react';
import { X, Wifi, WifiOff, Loader2, Ghost, DollarSign, KeyRound } from 'lucide-react';
import { useAuthStore } from '../../stores/useAuthStore.js';
import { useOpsStore } from '../../stores/useOpsStore.js';

export default function ConnectDialog({ onClose }) {
  const { ssidInput, isDemo, isConnecting, isDisconnecting, connectError, setSsidInput, setIsDemo, connect, disconnect } = useAuthStore();
  const { sessionStatus, balance, accountType } = useOpsStore();
  const sessionConnected = sessionStatus === 'connected';
  const overlayRef = useRef(null);

  // Close on Escape
  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  async function handleConnect() {
    await connect(ssidInput, isDemo);
    // Close on success (no error)
    if (!useAuthStore.getState().connectError) {
      onClose();
    }
  }

  async function handleDisconnect() {
    await disconnect();
    onClose();
  }

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2">
            {sessionConnected
              ? <Wifi size={16} className="text-emerald-400" />
              : <WifiOff size={16} className="text-slate-400" />}
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              {sessionConnected ? 'Session Active' : 'Connect Session'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-5 flex flex-col gap-4">
          {/* Connected state */}
          {sessionConnected ? (
            <div className="flex flex-col gap-3">
              <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700/40 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-sm font-medium text-emerald-700 dark:text-emerald-400">Connected</span>
                </div>
                {accountType && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                    {accountType === 'demo'
                      ? <Ghost size={11} className="text-amber-400" />
                      : <DollarSign size={11} className="text-emerald-400" />}
                    <span className="capitalize font-medium">{accountType}</span> account
                    {balance != null && <span className="ml-1">· ${balance.toFixed(2)}</span>}
                  </p>
                )}
              </div>

              <button
                onClick={handleDisconnect}
                disabled={isDisconnecting}
                className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-medium bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-700/40 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors disabled:opacity-50"
              >
                {isDisconnecting ? <Loader2 size={14} className="animate-spin" /> : <WifiOff size={14} />}
                Disconnect
              </button>
            </div>
          ) : (
            /* Connect form */
            <div className="flex flex-col gap-4">
              {/* Account type toggle */}
              <div>
                <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2 block">Account Type</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setIsDemo(true)}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium border transition-all ${
                      isDemo
                        ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-600/40 text-amber-600 dark:text-amber-400'
                        : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                  >
                    <Ghost size={12} />
                    Demo
                  </button>
                  <button
                    onClick={() => setIsDemo(false)}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium border transition-all ${
                      !isDemo
                        ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-300 dark:border-emerald-600/40 text-emerald-600 dark:text-emerald-400'
                        : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                  >
                    <DollarSign size={12} />
                    Real
                  </button>
                </div>
              </div>

              {/* SSID input */}
              <div>
                <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2 block flex items-center gap-1">
                  <KeyRound size={11} />
                  SSID Frame
                  <span className="text-slate-400 font-normal ml-1">(leave empty to auto-reconnect)</span>
                </label>
                <textarea
                  value={ssidInput}
                  onChange={(e) => setSsidInput(e.target.value)}
                  placeholder={'42["auth",{"session":"...","isDemo":1}]'}
                  rows={3}
                  className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-400/50 focus:border-sky-400 resize-none"
                />
              </div>

              {/* Error */}
              {connectError && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700/40 rounded-lg px-3 py-2">
                  <p className="text-xs text-red-600 dark:text-red-400">{connectError}</p>
                </div>
              )}

              {/* Connect button */}
              <button
                onClick={handleConnect}
                disabled={isConnecting}
                className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-medium bg-sky-500 hover:bg-sky-600 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isConnecting ? <Loader2 size={14} className="animate-spin" /> : <Wifi size={14} />}
                {isConnecting ? 'Connecting…' : 'Connect'}
              </button>

              <p className="text-[10px] text-slate-400 text-center">
                Get the SSID from Chrome DevTools → Network → WS tab after logging into Pocket Option.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
