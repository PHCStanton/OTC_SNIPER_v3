import { useSettingsStore } from '../../stores/useSettingsStore.js';

export default function AdaptiveExpirySettings() {
  const {
    minAdaptiveExpiry,
    setMinAdaptiveExpiry,
    adaptiveExpiryEnabled,
    setAdaptiveExpiryEnabled,
    autoGhostExpirationSeconds,
  } = useSettingsStore();

  return (
    <div className="space-y-3 border-t border-white/5 pt-3 mt-2">
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={adaptiveExpiryEnabled}
            onChange={(e) => setAdaptiveExpiryEnabled(e.target.checked)}
            className="accent-[#ffb800] rounded"
          />
          <span className={`text-[9px] font-black uppercase tracking-wider ${adaptiveExpiryEnabled ? 'text-[#ffb800]' : 'text-gray-400'}`}>
            Enable Adaptive Expiry Extension
          </span>
        </label>
        <span className={`px-1.5 py-0.5 text-[8px] font-black uppercase tracking-widest rounded ${
          adaptiveExpiryEnabled ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
        }`}>
          {adaptiveExpiryEnabled ? 'Active' : 'Disabled'}
        </span>
      </div>

      {adaptiveExpiryEnabled ? (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[8px] font-bold text-gray-400">Min Expiry Floor (Seconds)</span>
            <span className="text-[9px] font-black font-mono text-white">{minAdaptiveExpiry}s</span>
          </div>
          <input
            type="range"
            min="15"
            max="300"
            step="15"
            value={minAdaptiveExpiry}
            onChange={(e) => setMinAdaptiveExpiry(Number(e.target.value))}
            className="w-full accent-[#ffb800] cursor-pointer h-1 rounded-lg bg-[#25282f]"
          />
          <div className="text-[7px] text-gray-500">
            The minimum allowed broker interval (15s, 30s, 60s, 120s, 300s) for volatility-adaptive trade duration execution.
          </div>
        </div>
      ) : (
        <div className="rounded-lg bg-white/[0.02] border border-white/5 p-2 text.center">
          <p className="text-[8px] font-medium text-gray-400">
            Extension disabled. Trade expiry defaults to Ghost Parameters dropdown: <span className="font-black text-[#ffb800]">{autoGhostExpirationSeconds}s</span>.
          </p>
        </div>
      )}
    </div>
  );
}
