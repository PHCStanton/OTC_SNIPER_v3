/**
 * TopBar — Chrome badge + SSID/Session badge + Theme toggle + Tab toggle.
 * Driven by useOpsStore (live status from Socket.IO check_status polling).
 */
import { useState } from 'react';
import {
  Chrome,
  Wifi,
  WifiOff,
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
import { chromeStart, chromeStop } from '../../api/opsApi.js';
import ConnectDialog from '../auth/ConnectDialog.jsx';
import logoImg from '../../../assets/GOLD_LOGO1.jpg';

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
      <header className="flex h-16 items-center justify-between border-b border-white/10 bg-[#1a1717] px-6 shadow-2xl shadow-black/30 shrink-0 z-50">
        {/* ── Left: Logo + Tab Toggle ── */}
        <div className="flex items-center gap-1">
          <img src={logoImg} alt="OTC SNIPER" className="h-16 w-auto select-none" draggable={false} />
OTC SNIPER
          <div className="flex items-center gap-1 rounded-lg p-0.5">
            <button
              onClick={() => setDashboardMode('trading')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold uppercase tracking-wide transition-colors ${isTrading ? 'border-b-2 border-[#f5df19] text-[#f5df19]' : 'text-gray-500 hover:text-gray-300'}`}
            >
              <TrendingUp size={13} />
              Trading
            </button>
            <button
              onClick={() => setDashboardMode('risk')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold uppercase tracking-wide transition-colors ${!isTrading ? 'border-b-2 border-[#f5df19] text-[#f5df19]' : 'text-gray-500 hover:text-gray-300'}`}
            >
              <ShieldAlert size={13} />
              Risk Manager
            </button>
          </div>
        </div>

        {/* ── Right: Status badges + Settings ── */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleChromeToggle}
            disabled={chromeLoading}
            title={chromeRunning ? 'Chrome running — click to stop' : 'Chrome stopped — click to start'}
            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium select-none transition-colors ${chromeRunning ? 'border-[#f5df19]/30 bg-[#f5df19]/10 text-[#f5df19] hover:bg-[#f5df19]/20' : 'border-white/10 bg-[#212127] text-gray-500 hover:bg-[#282d2e]'}`}
          >
            {chromeLoading ? <Loader2 size={12} className="animate-spin" /> : <Chrome size={12} />}
            <span>Chrome</span>
            <span className={`h-1.5 w-1.5 rounded-full ${chromeRunning ? 'bg-[#f5df19]' : 'bg-gray-500'}`} />
          </button>

          <button
            onClick={() => setShowConnect(true)}
            title={sessionConnected ? 'Session connected — click to manage' : 'No session — click to connect'}
            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium select-none transition-colors ${sessionConnected ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-400 hover:bg-emerald-400/20' : 'border-white/10 bg-[#212127] text-gray-500 hover:bg-[#282d2e]'}`}
          >
            {sessionConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
            <span>{sessionConnected ? 'Connected' : 'Disconnected'}</span>
            {sessionConnected && accountType && (
              <span className={`inline-flex items-center gap-1 rounded px-1 py-0.5 text-[10px] font-bold leading-none ${accountType === 'demo' ? 'bg-[#f5df19]/20 text-[#f5df19]' : 'bg-emerald-400/20 text-emerald-400'}`}>
                {accountType === 'demo' ? <Ghost size={9} /> : <DollarSign size={9} />}
                {accountType.toUpperCase()}
              </span>
            )}
            {sessionConnected && balance != null && (
              <span className="font-normal text-gray-400">${balance.toFixed(2)}</span>
            )}
            <ChevronDown size={10} className="text-gray-500" />
          </button>

          <button
            onClick={() => setActiveView('settings')}
            className="rounded-md p-1.5 text-gray-500 transition-colors hover:bg-white/5 hover:text-gray-300"
            title="Settings"
          >
            <Settings size={25} />
          </button>
        </div>
      </header>

      {showConnect && <ConnectDialog onClose={() => setShowConnect(false)} />}
    </>
  );
}
