/**
 * AccountSettings — session identity, saved SSIDs, and Auth0-ready boundary.
 */
import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Loader2, RefreshCcw, Shield, Trash2, UserRound, Wifi, WifiOff } from 'lucide-react';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { sessionClearSsid, sessionSsidStatus } from '../../api/opsApi.js';

function PanelCard({ title, subtitle, children, className = '' }) {
  return (
    <section className={`rounded-3xl border border-white/5 bg-[#151a22]/95 p-5 shadow-[0_15px_40px_rgba(0,0,0,0.28)] ${className}`}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-bold tracking-tight text-[#e3e6e7]">{title}</h3>
          {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
        </div>
        {children && <div className="shrink-0" />}
      </div>
      {children}
    </section>
  );
}

function StatusBadge({ tone = 'neutral', children }) {
  const tones = {
    neutral: 'border-white/5 bg-white/5 text-gray-400',
    emerald: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-400',
    amber: 'border-[#f5df19]/20 bg-[#f5df19]/10 text-[#f5df19]',
    rose: 'border-red-400/20 bg-red-400/10 text-red-400',
  };

  return <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${tones[tone]}`}>{children}</span>;
}

function SSIDRow({ label, saved, demo, busy, onClear }) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-white/5 bg-[#0f1419] px-4 py-4 md:flex-row md:items-center md:justify-between">
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl ${saved ? 'bg-emerald-400/10 text-emerald-400' : 'bg-white/5 text-gray-500'}`}>
          {saved ? <CheckCircle2 size={16} /> : <WifiOff size={16} />}
        </div>
        <div>
          <p className="text-sm font-bold text-[#e3e6e7]">{label}</p>
          <p className="mt-1 text-xs text-gray-500">{saved ? 'Saved in .env and available for auto-reconnect.' : 'No saved SSID found.'}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 md:justify-end">
        <StatusBadge tone={saved ? 'emerald' : 'neutral'}>{saved ? 'Saved' : 'Empty'}</StatusBadge>
        <button
          type="button"
          onClick={onClear}
          disabled={!saved || busy}
          className="inline-flex items-center gap-1.5 rounded-full border border-red-400/20 bg-red-400/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-red-400 transition-colors hover:bg-red-400/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
          Clear saved SSID
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
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <PanelCard title="Session identity" subtitle="This panel stays focused on broker/session state only.">
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-white/5 bg-[#0f1419] px-4 py-4">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">Broker</p>
            <div className="mt-2 flex items-center gap-2">
              <Shield size={16} className="text-[#f5df19]" />
              <span className="text-sm font-bold text-[#e3e6e7]">Pocket Option</span>
            </div>
          </div>

          <div className="rounded-2xl border border-white/5 bg-[#0f1419] px-4 py-4">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">Connection</p>
            <div className="mt-2 flex items-center gap-2">
              {sessionConnected ? <Wifi size={16} className="text-emerald-400" /> : <WifiOff size={16} className="text-gray-500" />}
              <span className="text-sm font-bold text-[#e3e6e7]">{sessionConnected ? 'Connected' : 'Disconnected'}</span>
            </div>
            <p className="mt-2 text-xs text-gray-500">Chrome: {chromeRunning ? 'running' : 'stopped'} · Account: {accountType ? accountType.toUpperCase() : '—'}</p>
            <p className="mt-1 text-xs text-gray-500">Balance: ${Number(balance || 0).toFixed(2)}</p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <StatusBadge tone={chromeRunning ? 'emerald' : 'neutral'}>Chrome {chromeRunning ? 'running' : 'stopped'}</StatusBadge>
          <StatusBadge tone={sessionConnected ? 'emerald' : 'neutral'}>Session {sessionConnected ? 'active' : 'idle'}</StatusBadge>
          <StatusBadge tone={accountType === 'real' ? 'emerald' : accountType === 'demo' ? 'amber' : 'neutral'}>{accountType ? `${accountType} account` : 'no account'}</StatusBadge>
        </div>
      </PanelCard>

      <PanelCard title="Auth0-ready boundary" subtitle="Future user profile state belongs in useUserStore, not useAuthStore.">
        <div className="rounded-2xl border border-[#f5df19]/20 bg-[#f5df19]/10 px-4 py-4 text-sm text-[#e3e6e7]">
          <div className="flex items-center gap-2 font-semibold text-[#f5df19]">
            <UserRound size={16} />
            Reserved profile surface
          </div>
          <p className="mt-2 text-xs leading-6 text-gray-300">
            Session connect / disconnect stays in the auth store. A future Auth0 profile panel can live beside it without changing SSID session flows.
          </p>
        </div>

        <div className="mt-4 rounded-2xl border border-white/5 bg-[#0f1419] px-4 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">Saved SSID inventory</p>
          <div className="mt-2 flex items-center justify-between gap-3">
            <p className="text-xs text-gray-400">Refresh to re-read saved demo / real frames from .env.</p>
            <button
              type="button"
              onClick={() => void refreshSavedStatus()}
              className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-300 transition-colors hover:bg-white/10"
            >
              {loadingStatus ? <Loader2 size={12} className="animate-spin" /> : <RefreshCcw size={12} />}
              Refresh
            </button>
          </div>

          <div className="mt-4 space-y-3">
            {error && (
              <div className="flex items-start gap-2 rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-red-300">
                <AlertTriangle size={15} className="mt-0.5 shrink-0" />
                <p className="text-xs leading-5">{error}</p>
              </div>
            )}

            <SSIDRow
              label="Demo SSID"
              saved={savedStatus.has_demo_ssid}
              demo
              busy={actionBusy}
              onClear={() => void handleClearSavedSsid(true)}
            />

            <SSIDRow
              label="Real SSID"
              saved={savedStatus.has_real_ssid}
              demo={false}
              busy={actionBusy}
              onClear={() => void handleClearSavedSsid(false)}
            />
          </div>
        </div>
      </PanelCard>
    </div>
  );
}