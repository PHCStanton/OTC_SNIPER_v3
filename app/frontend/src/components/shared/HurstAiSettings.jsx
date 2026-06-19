import { useSettingsStore } from '../../stores/useSettingsStore.js';

export default function HurstAiSettings() {
  const {
    hurstMinScaleCutoff,
    hurstAiConfidenceThreshold,
    setHurstMinScaleCutoff,
    setHurstAiConfidenceThreshold,
  } = useSettingsStore();

  return (
    <div className="space-y-3 border-t border-white/5 pt-3 mt-2">
      <div className="flex items-center justify-between">
        <span className="text-[8.5px] font-black uppercase tracking-wider text-purple-400">
          AI Pulse & Noise Filter Settings
        </span>
      </div>
      
      {/* Min Scale Cutoff slider */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[8px] font-bold text-gray-400">Microstructure Scale Cutoff</span>
          <span className="text-[9px] font-black font-mono text-white">{hurstMinScaleCutoff} Ticks</span>
        </div>
        <input
          type="range"
          min="4"
          max="30"
          step="1"
          value={hurstMinScaleCutoff}
          onChange={(e) => setHurstMinScaleCutoff(Number(e.target.value))}
          className="w-full accent-purple-500 cursor-pointer h-1 rounded-lg bg-[#25282f]"
        />
        <div className="text-[7px] text-gray-500">
          Excludes shorter scales below this cutoff to filter bid-ask bounce noise.
        </div>
      </div>

      {/* AI Confidence Threshold slider */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[8px] font-bold text-gray-400">Elite AI Confidence Floor</span>
          <span className="text-[9px] font-black font-mono text-white">{hurstAiConfidenceThreshold}%</span>
        </div>
        <input
          type="range"
          min="50"
          max="95"
          step="1"
          value={hurstAiConfidenceThreshold}
          onChange={(e) => setHurstAiConfidenceThreshold(Number(e.target.value))}
          className="w-full accent-purple-500 cursor-pointer h-1 rounded-lg bg-[#25282f]"
        />
        <div className="text-[7px] text-gray-500">
          Vetoes trades if the combined OTEO AI confidence score is below this floor.
        </div>
      </div>
    </div>
  );
}
