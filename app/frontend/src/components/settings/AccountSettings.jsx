/**
 * AccountSettings — session identity, saved SSIDs, and Auth0-ready boundary.
 * Redesigned to follow the Stitch Design Reference.
 */
import { useEffect, useState } from 'react';
import { 
  AlertTriangle, CheckCircle2, Loader2, RefreshCcw, 
  Shield, Trash2, UserRound, Wifi, WifiOff 
} from 'lucide-react';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { sessionClearSsid, sessionSsidStatus } from '../../api/opsApi.js';
import { SectionCard } from '../shared/StitchComponents.jsx';

function StatusBadge({ tone = 'neutral', children }) {
  const tones = {
    neutral: 'border-white/5 bg-white/[0.02] text-gray-500',
    emerald: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400',
    amber: 'border-[#ffb800]/20 bg-[#ffb800]/10 text-[#ffb800]',
    rose: 'border-red-500/20 bg-red-500/10 text-red-400',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[9px] font-black uppercase tracking-widest ${tones[tone]}`}>
      {children}
    </span>
  );
}

function SSIDRow({ label, saved, demo, busy, onClear }) {
  return (
    <div className="flex flex-col gap-4 rounded-xl border border-white/5 bg-[#25282f]/30 px-5 py-5 md:flex-row md:items-center md:justify-between transition duration-300 hover:border-white/10">
      <div className="flex items-start gap-4">
        <div className={`mt-0.5 flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border ${
          saved ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400' : 'border-white/5 bg-white/[0.02] text-gray-600'
        }`}>
          {saved ? <CheckCircle2 size={20} /> : <WifiOff size={20} />}
        </div>
        <div>
          <p className="text-sm font-black uppercase tracking-wider text-white">{label}</p>
          <p className="mt-1 text-xs font-medium text-gray-500 uppercase leading-relaxed">
            {saved ? 'SSID credentials active in .env and primed for auto-reconnect.' : 'No active session token detected.'}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 md:justify-end">
        <StatusBadge tone={saved ? 'emerald' : 'neutral'}>{saved ? 'Primed' : 'Empty'}</StatusBadge>
        <button
          type="button"
          onClick={onClear}
          disabled={!saved || busy}
          className="inline-flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-2.5 text-[10px] font-black uppercase tracking-widest text-red-400 transition hover:bg-red-500/15 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-30"
        >
          {busy ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
          Decommit SSID
        </button>
      </div>
    </div>
  );
}

export default function AccountSettings() {
  const { sessionStatus, chromeStatus, balance, accountType } = useOpsStore();
  const [savedStatus, setSavedStatus] = useState({ has_demo_ssid: false, has_real_ssid: false });
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [actionBusy, setActionBusy] = useState(false);
  const [error, setError] = useState(null);

  const sessionConnected = sessionStatus === 'connected';
  const chromeRunning = chromeStatus === 'running';

  async function refreshSavedStatus() {
    setLoadingStatus(true);
    setError(null);
    try {
      const data = await sessionSsidStatus();
      setSavedStatus({
        has_demo_ssid: Boolean(data.has_demo_ssid),
        has_real_ssid: Boolean(data.has_real_ssid),
      });
    } catch (err) {
      setError(err.message || 'Unable to load saved SSID status.');
    } finally {
      setLoadingStatus(false);
    }
  }

  useEffect(() => {
    void refreshSavedStatus();
  }, []);

  async function handleClearSavedSsid(demo) {
    const label = demo ? 'demo' : 'real';
    setActionBusy(true);
    setError(null);
    try {
      const data = await sessionClearSsid(demo);
      setSavedStatus({
        has_demo_ssid: Boolean(data.has_demo_ssid),
        has_real_ssid: Boolean(data.has_real_ssid),
      });
    } catch (err) {
      setError(`Failed to clear ${label} SSID: ${err.message || 'Unknown error'}`);
    } finally {
      setActionBusy(false);
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <SectionCard 
        title="Session Identity" 
        subtitle="Active broker configuration and session network state."
        icon={UserRound}
      >
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-white/5 bg-[#25282f]/30 px-5 py-5">
            <p className="text-[10px] font-black uppercase tracking-widest text-gray-500">Target Broker</p>
            <div className="mt-3 flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#ffb800]/10 text-[#ffb800]">
                <Shield size={18} />
              </div>
              <span className="text-base font-black uppercase tracking-wider text-white">Pocket Option</span>
            </div>
          </div>

          <div className="rounded-xl border border-white/5 bg-[#25282f]/30 px-5 py-5">
            <p className="text-[10px] font-black uppercase tracking-widest text-gray-500">Telemetry Status</p>
            <div className="mt-3 flex items-center gap-3">
              <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                sessionConnected ? 'bg-emerald-500/10 text-emerald-400' : 'bg-white/5 text-gray-500'
              }`}>
                {sessionConnected ? <Wifi size={18} /> : <WifiOff size={18} />}
              </div>
              <span className="text-base font-black uppercase tracking-wider text-white">
                {sessionConnected ? 'Online' : 'Offline'}
              </span>
            </div>
            <div className="mt-4 space-y-2 border-t border-white/5 pt-3 text-[11px] font-bold uppercase tracking-wider text-gray-500">
              <p>Container Engine: <span className={chromeRunning ? 'text-emerald-400' : 'text-gray-400'}>{chromeRunning ? 'Active' : 'Halted'}</span></p>
              <p>Sizing Profile: <span className="text-white">{accountType ? accountType : 'UNRESOLVED'}</span></p>
              <p>Margin Balance: <span className="text-[#ffb800]">${Number(balance || 0).toFixed(2)}</span></p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 pt-2 border-t border-white/5">
          <StatusBadge tone={chromeRunning ? 'emerald' : 'neutral'}>Engine {chromeRunning ? 'running' : 'stopped'}</StatusBadge>
          <StatusBadge tone={sessionConnected ? 'emerald' : 'neutral'}>Socket {sessionConnected ? 'connected' : 'disconnected'}</StatusBadge>
          <StatusBadge tone={accountType === 'real' ? 'emerald' : accountType === 'demo' ? 'amber' : 'neutral'}>
            {accountType ? `${accountType} mode` : 'No active run'}
          </StatusBadge>
        </div>
      </SectionCard>

      <SectionCard 
        title="Identity Safeguard" 
        subtitle="Isolated credential boundary reserved for secure sessions."
        icon={Shield}
      >
        <div className="rounded-xl border border-[#ffb800]/25 bg-[#ffb800]/5 px-5 py-5 text-sm text-[#e3e6e7] shadow-[inset_0_0_15px_rgba(255,184,0,0.02)]">
          <div className="flex items-center gap-3 font-black uppercase tracking-wider text-[#ffb800]">
            <UserRound size={18} />
            Secure Profile Boundary
          </div>
          <p className="mt-3 text-xs font-medium uppercase tracking-normal leading-relaxed text-gray-400">
            Session credentials are held securely in memory. A future Auth0 profile integration will operate adjacent to this container without exposing active SSID tokens.
          </p>
        </div>

        <div className="mt-4 rounded-xl border border-white/5 bg-[#25282f]/20 p-5">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/5 pb-4">
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-gray-500">SSID Registry</p>
              <p className="mt-1 text-xs font-medium text-gray-600 uppercase">Synchronize local environment descriptors.</p>
            </div>
            <button
              type="button"
              onClick={() => void refreshSavedStatus()}
              className="inline-flex items-center gap-2 rounded-lg border border-white/5 bg-[#25282f] px-4 py-2.5 text-[10px] font-black uppercase tracking-widest text-gray-400 transition hover:bg-[#2d3139] hover:text-white"
            >
              {loadingStatus ? <Loader2 size={12} className="animate-spin" /> : <RefreshCcw size={12} />}
              Resync
            </button>
          </div>

          <div className="mt-4 space-y-4">
            {error && (
              <div className="flex items-start gap-3 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-4 text-red-300">
                <AlertTriangle size={18} className="shrink-0 text-red-400" />
                <p className="text-xs font-semibold uppercase tracking-wider">{error}</p>
              </div>
            )}

            <SSIDRow
              label="Demo Account SSID"
              saved={savedStatus.has_demo_ssid}
              demo
              busy={actionBusy}
              onClear={() => void handleClearSavedSsid(true)}
            />

            <SSIDRow
              label="Real Account SSID"
              saved={savedStatus.has_real_ssid}
              demo={false}
              busy={actionBusy}
              onClear={() => void handleClearSavedSsid(false)}
            />
          </div>
        </div>
      </SectionCard>
    </div>
  );
}