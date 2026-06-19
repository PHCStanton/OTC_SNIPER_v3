import { useSettingsStore } from '../../stores/useSettingsStore.js';

export default function HurstExpirySettings() {
  const {
    hurstMeanRevertThreshold,
    hurstTrendThreshold,
    minAdaptiveExpiry,
    setHurstMeanRevertThreshold,
    setHurstTrendThreshold,
    setMinAdaptiveExpiry,
  } = useSettingsStore();

  return (
    <div className="space-y-3 border-t border-white/5 pt-3 mt-2">
      <div className="flex items-center justify-between">
        <span className="text-[8.5px] font-black uppercase tracking-wider text-[#ffb800]">
          Adaptive Expiry Settings
        </span>
      </div>
      
      {/* Mean Reversion Threshold slider */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[8px] font-bold text-gray-400">Mean Reversion Threshold (H)</span>
          <span className="text-[9px] font-black font-mono text-white">{hurstMeanRevertThreshold.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0.30"
          max="0.50"
          step="0.01"
          value={hurstMeanRevertThreshold}
          onChange={(e) => setHurstMeanRevertThreshold(Number(e.target.value))}
          className="w-full accent-[#ffb800] cursor-pointer h-1 rounded-lg bg-[#25282f]"
        />
        <div className="text-[7px] text-gray-500">
          Hurst values below this trigger anti-persistent mean reversion strategy.
        </div>
      </div>

      {/* Trend Threshold slider */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[8px] font-bold text-gray-400">Trend Threshold (H)</span>
          <span className="text-[9px] font-black font-mono text-white">{hurstTrendThreshold.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0.50"
          max="0.70"
          step="0.01"
          value={hurstTrendThreshold}
          onChange={(e) => setHurstTrendThreshold(Number(e.target.value))}
          className="w-full accent-[#ffb800] cursor-pointer h-1 rounded-lg bg-[#25282f]"
        />
        <div className="text-[7px] text-gray-500">
          Hurst values above this mark strong, persistent momentum trending.
        </div>
      </div>

      {/* Minimum Expiry duration */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[8px] font-bold text-gray-400">Min Expiry (Seconds)</span>
          <span className="text-[9px] font-black font-mono text-white">{minAdaptiveExpiry}s</span>
        </div>
        <input
          type="range"
          min="10"
          max="300"
          step="5"
          value={minAdaptiveExpiry}
          onChange={(e) => setMinAdaptiveExpiry(Number(e.target.value))}
          className="w-full accent-[#ffb800] cursor-pointer h-1 rounded-lg bg-[#25282f]"
        />
        <div className="text-[7px] text-gray-500">
          Base option expiration period for anti-persistent trades.
        </div>
      </div>
    </div>
  );
}
