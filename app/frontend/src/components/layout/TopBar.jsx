/**
 * TopBar — Chrome badge + SSID/Session badge + Theme toggle + Tab toggle.
 * Driven by useOpsStore (live status from Socket.IO check_status polling).
 */
import { useState } from 'react';
import {
  Chrome,
  Wifi,
  WifiOff,
  Monitor,
  TrendingUp,
  ShieldAlert,
  Settings,
  ChevronDown,
  Loader2,
  DollarSign,
  Ghost,
} from 'lucide-react';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { useLayoutStore } from '../../stores/useLayoutStore.js';
import { useAuthStore } from '../../stores/useAuthStore.js';
import { chromeStart, chromeStop } from '../../api/opsApi.js';
import ConnectDialog from '../auth/ConnectDialog.jsx';
import logoImg from '../../../assets/LOGO1-bg.png';

export default function TopBar() {
  const { chromeStatus, sessionStatus, balance, accountType, setChromeStatus } = useOpsStore();
  const { dashboardMode, setDashboardMode, setActiveView } = useLayoutStore();
  const [showConnect, setShowConnect] = useState(false);
  const [chromeLoading, setChromeLoading] = useState(false);

  const isTrading = dashboardMode === 'trading';
  const chromeRunning = chromeStatus === 'running';
  const sessionConnected = sessionStatus === 'connected';

  async function handleChromeToggle() {
    setChromeLoading(true);
    try {
      if (chromeRunning) {
        await chromeStop();
        setChromeStatus('stopped');
      } else {
        await chromeStart();
        setChromeStatus('running');
      }
    } catch (err) {
      console.error('[TopBar] Chrome toggle error:', err.message);
    } finally {
      setChromeLoading(false);
    }
  }

  return (
    <>
      <header className="
        flex items-center justify-between
        h-12 px-4
        border-b border-slate-200 dark:border-slate-700
        bg-white dark:bg-slate-900
        shrink-0 z-50
      ">
        {/* ── Left: Logo + Tab Toggle ── */}
        <div className="flex items-center gap-4">
          <img
            src={logoImg}
            alt="OTC SNIPER"
            className="h-10 w-auto select-none"
            draggable={false}
          />

          {/* Tab toggle */}
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5">
            <button
              onClick={() => setDashboardMode('trading')}
              className={`
                flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all
                ${isTrading
                  ? 'bg-white dark:bg-slate-700 text-sky-500 shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'}
              `}
            >
              <TrendingUp size={13} />
              Trading
            </button>
            <button
              onClick={() => setDashboardMode('risk')}
              className={`
                flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all
                ${!isTrading
                  ? 'bg-white dark:bg-slate-700 text-amber-400 shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'}
              `}
            >
              <ShieldAlert size={13} />
              Risk Manager
            </button>
          </div>
        </div>

        {/* ── Right: Status badges + Settings ── */}
        <div className="flex items-center gap-2">

          {/* Chrome badge */}
          <button
            onClick={handleChromeToggle}
            disabled={chromeLoading}
            title={chromeRunning ? 'Chrome running — click to stop' : 'Chrome stopped — click to start'}
            className={`
              flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
              border transition-all select-none
              ${chromeRunning
                ? 'border-sky-400/50 bg-sky-400/10 text-sky-400 hover:bg-sky-400/20'
                : 'border-slate-300 dark:border-slate-600 bg-slate-100 dark:bg-slate-800 text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'}
            `}
          >
            {chromeLoading
              ? <Loader2 size={12} className="animate-spin" />
              : <Chrome size={12} />}
            <span>{chromeRunning ? 'Chrome' : 'Chrome'}</span>
            <span className={`w-1.5 h-1.5 rounded-full ${chromeRunning ? 'bg-sky-400' : 'bg-slate-400'}`} />
          </button>

          {/* Session badge */}
          <button
            onClick={() => setShowConnect(true)}
            title={sessionConnected ? 'Session connected — click to manage' : 'No session — click to connect'}
            className={`
              flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
              border transition-all select-none
              ${sessionConnected
                ? 'border-emerald-400/50 bg-emerald-400/10 text-emerald-400 hover:bg-emerald-400/20'
                : 'border-slate-300 dark:border-slate-600 bg-slate-100 dark:bg-slate-800 text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'}
            `}
          >
            {sessionConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
            <span>{sessionConnected ? 'Connected' : 'Disconnected'}</span>
            {sessionConnected && accountType && (
              <span className={`
                px-1 py-0.5 rounded text-[10px] font-bold leading-none
                ${accountType === 'demo'
                  ? 'bg-amber-400/20 text-amber-400'
                  : 'bg-emerald-400/20 text-emerald-400'}
              `}>
                {accountType === 'demo' ? <Ghost size={9} className="inline" /> : <DollarSign size={9} className="inline" />}
                {' '}{accountType.toUpperCase()}
              </span>
            )}
            {sessionConnected && balance > 0 && (
              <span className="text-slate-500 dark:text-slate-400 font-normal">
                ${balance.toFixed(2)}
              </span>
            )}
            <ChevronDown size={10} className="text-slate-400" />
          </button>

          {/* Settings button */}
          <button
            onClick={() => setActiveView('settings')}
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title="Settings"
          >
            <Settings size={15} />
          </button>
        </div>
      </header>

      {showConnect && <ConnectDialog onClose={() => setShowConnect(false)} />}
    </>
  );
}
