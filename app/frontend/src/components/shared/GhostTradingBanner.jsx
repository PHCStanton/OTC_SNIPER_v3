/**
 * GhostTradingBanner — persistent top-of-workspace banner shown when ghost trading is active.
 * Driven by useSettingsStore.ghostTradingEnabled.
 * Provides a one-click toggle to exit ghost mode.
 */
import { Ghost, X } from 'lucide-react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';

export default function GhostTradingBanner() {
  const { ghostTradingEnabled, setGhostTradingEnabled } = useSettingsStore();

  if (!ghostTradingEnabled) return null;

  return (
    <div
      role="status"
      aria-label="Ghost trading mode active"
      className="flex items-center justify-between gap-3 rounded-xl border border-[#f5df19]/20 bg-[#1f1a00] px-4 py-2.5 text-[#f5df19] shadow-lg shadow-[#f5df19]/5"
    >
      <div className="flex items-center gap-2">
        <Ghost size={15} className="shrink-0" />
        <p className="text-xs font-semibold">
          Ghost Trading Mode — trades are simulated and will not affect your live account balance.
        </p>
      </div>
      <button
        type="button"
        onClick={() => setGhostTradingEnabled(false)}
        className="shrink-0 rounded-md p-1 opacity-60 hover:opacity-100 transition-opacity"
        aria-label="Exit ghost trading mode"
        title="Exit ghost trading mode"
      >
        <X size={13} />
      </button>
    </div>
  );
}
