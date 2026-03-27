/**
 * TradingPlaceholder — shown in the main content area for the Trading view.
 * Phase 5 will replace this with the real trading UI.
 */
import { TrendingUp, Wifi, WifiOff, Activity } from 'lucide-react';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { useAssetStore } from '../../stores/useAssetStore.js';

export default function TradingPlaceholder() {
  const { sessionStatus, chromeStatus } = useOpsStore();
  const { selectedAsset } = useAssetStore();

  const sessionConnected = sessionStatus === 'connected';
  const chromeRunning = chromeStatus === 'running';

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 p-8">
      {/* Status indicators */}
      <div className="flex items-center gap-3">
        <StatusPill
          icon={Activity}
          label="Chrome"
          active={chromeRunning}
          activeColor="text-sky-400"
          activeBg="bg-sky-400/10 border-sky-400/30"
        />
        <StatusPill
          icon={sessionConnected ? Wifi : WifiOff}
          label={sessionConnected ? 'Session Active' : 'No Session'}
          active={sessionConnected}
          activeColor="text-emerald-400"
          activeBg="bg-emerald-400/10 border-emerald-400/30"
        />
      </div>

      {/* Main placeholder */}
      <div className="text-center max-w-sm">
        <div className="w-16 h-16 rounded-2xl bg-sky-400/10 border border-sky-400/20 flex items-center justify-center mx-auto mb-4">
          <TrendingUp size={28} className="text-sky-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2">
          Trading View
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">
          Selected asset: <span className="font-medium text-sky-400">{selectedAsset}</span>
        </p>
        <p className="text-xs text-slate-400 dark:text-slate-500">
          Phase 5 — Chart, signal ring, and trade panel coming next.
        </p>
      </div>

      {/* Connection guidance */}
      {!sessionConnected && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/40 rounded-xl p-4 max-w-sm text-center">
          <p className="text-xs text-amber-700 dark:text-amber-400 font-medium">
            Connect a session to start trading.
          </p>
          <p className="text-xs text-amber-600 dark:text-amber-500 mt-1">
            Use the <span className="font-semibold">Disconnected</span> badge in the top bar.
          </p>
        </div>
      )}
    </div>
  );
}

function StatusPill({ icon: Icon, label, active, activeColor, activeBg }) {
  return (
    <div className={`
      flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border
      ${active
        ? `${activeBg} ${activeColor}`
        : 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-400'}
    `}>
      <Icon size={12} />
      {label}
      <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-current' : 'bg-slate-400'}`} />
    </div>
  );
}
