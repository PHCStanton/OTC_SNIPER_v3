/**
 * TopBar — Chrome badge + SSID/Session badge + Theme toggle + Tab toggle.
 * Driven by useOpsStore (live status from Socket.IO check_status polling).
 */
import { useState } from 'react';
import {
  Bell,
  BookOpen,
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
import { useToastStore } from '../../stores/useToastStore.js';
import { chromeStart, chromeStop } from '../../api/opsApi.js';
import ConnectDialog from '../auth/ConnectDialog.jsx';
import logoImg from '../../../assets/GOLD_TARGET_LOGO1_RM.png';

export default function TopBar() {
  const { chromeStatus, sessionStatus, balance, accountType, setChromeStatus } = useOpsStore();
  const { activeView, dashboardMode, setDashboardMode, setActiveView } = useLayoutStore();
  const [showConnect, setShowConnect] = useState(false);
  const [chromeLoading, setChromeLoading] = useState(false);

  const isTrading = activeView !== 'journal' && activeView !== 'settings' && activeView !== 'ai' && dashboardMode === 'trading';
  const isRisk = activeView !== 'journal' && activeView !== 'settings' && activeView !== 'ai' && dashboardMode === 'risk';
  const isJournal = activeView === 'journal';
  const isAI = activeView === 'ai';
  const isSettings = activeView === 'settings';
  const chromeRunning = chromeStatus === 'running';
  const sessionConnected = sessionStatus === 'connected';
  const balanceLabel = `$${Number(balance || 0).toFixed(2)}`;

  async function handleChromeToggle() {
    setChromeLoading(true);
    try {
      if (chromeRunning) {
        await chromeStop();
        setChromeStatus('stopped');
        useToastStore.getState().addToast({ type: 'info', message: 'Chrome stopped.' });
      } else {
        await chromeStart();
        setChromeStatus('running');
        useToastStore.getState().addToast({ type: 'success', message: 'Chrome started — ready for SSID.' });
      }
    } catch (err) {
      console.error('[TopBar] Chrome toggle error:', err.message);
      useToastStore.getState().addToast({ type: 'error', message: `Chrome error: ${err.message}` });
    } finally {
      setChromeLoading(false);
    }
  }

  function handleNotificationsPlaceholder() {
    useToastStore.getState().addToast({ type: 'info', message: 'Notifications placeholder — system not wired yet.' });
  }

  return (
    <>
      <header className="flex h-16 items-center justify-between border-b border-white/5 bg-[#1a1c22] px-6 shadow-xl shrink-0 z-50">
        {/* ── Left: Logo + Connections ── */}
        <div className="flex items-center gap-1">
          <img src={logoImg} alt="OTC SNIPER" className="h-15 w-auto select-none" draggable={false} />
          <div className="flex items-center gap-3 ml-4">
            <button
              onClick={handleChromeToggle}
              disabled={chromeLoading}
              title={chromeRunning ? 'Chrome running — click to stop' : 'Chrome stopped — click to start'}
              className={`flex items-center gap-2 rounded-lg border px-3.5 py-2 text-[10px] font-black uppercase tracking-widest select-none transition-all duration-300 ${
                chromeRunning 
                  ? 'border-[#ffb800]/30 bg-[#ffb800]/10 text-[#ffb800] hover:bg-[#ffb800]/20' 
                  : 'border-white/5 bg-[#25282f]/30 text-gray-500 hover:bg-[#25282f]'
              }`}
            >
              {chromeLoading ? <Loader2 size={12} className="animate-spin" /> : <Chrome size={12} />}
              <span>Chrome</span>
              <span className={`h-1.5 w-1.5 rounded-full ${chromeRunning ? 'bg-[#ffb800]' : 'bg-gray-600'}`} />
            </button>
 
            <button
              onClick={() => setShowConnect(true)}
              title={sessionConnected ? 'Session connected — click to manage' : 'No session — click to connect'}
              className={`flex items-center gap-2 rounded-lg border px-3.5 py-2 text-[10px] font-black uppercase tracking-widest select-none transition-all duration-300 ${
                sessionConnected 
                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20' 
                  : 'border-white/5 bg-[#25282f]/30 text-gray-500 hover:bg-[#25282f]'
              }`}
            >
              {sessionConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
              <span>{sessionConnected ? 'Online' : 'Offline'}</span>
              {sessionConnected && accountType && (
                <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[8px] font-black tracking-widest ${
                  accountType === 'demo' ? 'bg-[#ffb800]/20 text-[#ffb800]' : 'bg-emerald-500/20 text-emerald-400'
                }`}>
                  {accountType === 'demo' ? <Ghost size={9} /> : <DollarSign size={9} />}
                  {accountType.toUpperCase()}
                </span>
              )}
              {sessionConnected && balance != null && (
                <span className="font-bold text-gray-400">${balance.toFixed(2)}</span>
              )}
              <ChevronDown size={10} className="text-gray-500" />
            </button>
          </div>
        </div>
 
        {/* ── Right: Tabs menu + Settings + Profile ── */}
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-2 rounded-lg p-0.5">
            <button
              onClick={() => setActiveView('journal')}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-[10px] font-black uppercase tracking-widest transition-all duration-300 ${
                isJournal 
                  ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/20' 
                  : 'text-gray-500 hover:text-gray-300 hover:bg-[#25282f]/20'
              }`}
            >
              <BookOpen size={12} />
              Journal
            </button>
            <button
              onClick={() => {
                setActiveView('risk');
                setDashboardMode('risk');
              }}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-[10px] font-black uppercase tracking-widest transition-all duration-300 ${
                isRisk 
                  ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/20' 
                  : 'text-gray-500 hover:text-gray-300 hover:bg-[#25282f]/20'
              }`}
            >
              <ShieldAlert size={12} />
              Risk
            </button>
            <button
              onClick={() => {
                setActiveView('trading');
                setDashboardMode('trading');
              }}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-[10px] font-black uppercase tracking-widest transition-all duration-300 ${
                isTrading 
                  ? 'bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/20' 
                  : 'text-gray-500 hover:text-gray-300 hover:bg-[#25282f]/20'
              }`}
            >
              <TrendingUp size={12} />
              Trading
            </button>
 
            <button
              onClick={() => setActiveView('ai')}
              title="AI Assistant"
              className={`ml-2 flex items-center justify-center rounded-lg border transition-all duration-350 ${
                isAI 
                  ? 'border-[#ffb800]/40 bg-[#ffb800]/10 shadow-[0_0_15px_rgba(255,184,0,0.12)] scale-105' 
                  : 'border-transparent bg-transparent hover:bg-white/5 grayscale hover:grayscale-0'
              }`}
            >
              <AiChipIcon size={38} />
            </button>
          </div>
 
          <div className="flex items-center gap-2 border-l border-white/5 pl-4">
            <TopBarIconButton
              onClick={() => setActiveView('settings')}
              title="Settings"
              ariaLabel="Open settings"
              active={isSettings}
            >
              <Settings size={22} strokeWidth={2} />
            </TopBarIconButton>
 
            <button
              type="button"
              className="flex h-11 w-11 items-center justify-center rounded-full border border-white/5 bg-[#25282f]/50 p-0.5 transition hover:border-[#ffb800]/30 hover:bg-[#2d3139]"
              title="Profile"
            >
              <img
                src="/Sci-fi_GUY.jpg"
                alt="Profile"
                className="h-9 w-9 rounded-full object-cover"
              />
            </button>
 
            <div className="flex h-11 min-w-[170px] items-center gap-3 rounded-lg border border-white/5 bg-[#25282f]/30 px-4">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-[#ffb800]/10 text-[#ffb800]">
                <DollarSign size={12} />
              </div>
              <span className="text-md font-black tracking-tight text-white">{balanceLabel}</span>
            </div>
 
            <TopBarIconButton
              onClick={handleNotificationsPlaceholder}
              title="Notifications placeholder"
              ariaLabel="Notifications placeholder"
            >
              <Bell size={20} strokeWidth={2} />
            </TopBarIconButton>
          </div>
        </div>
      </header>
 
      {showConnect && <ConnectDialog onClose={() => setShowConnect(false)} />}
    </>
  );
}
 
function TopBarIconButton({ active = false, onClick, title, ariaLabel, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-label={ariaLabel}
      className={`flex h-11 w-11 items-center justify-center rounded-lg border transition-all duration-300 ${
        active 
          ? 'border-[#ffb800]/30 bg-[#ffb800]/10 text-[#ffb800] shadow-[0_0_10px_rgba(255,184,0,0.05)]' 
          : 'border-transparent bg-transparent text-gray-500 hover:border-white/5 hover:bg-[#25282f]/45 hover:text-white'
      }`}
    >
      {children}
    </button>
  );
}

function AiChipIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="chipBodyGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#334155" />
          <stop offset="100%" stopColor="#0f172a" />
        </linearGradient>
        <filter id="chipGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
      <rect x="32" y="2" width="4" height="12" rx="1" fill="#94a3b8" />
      <rect x="48" y="0" width="4" height="14" rx="1" fill="#f5df19" />
      <rect x="64" y="2" width="4" height="12" rx="1" fill="#94a3b8" />
      <rect x="32" y="86" width="4" height="12" rx="1" fill="#94a3b8" />
      <rect x="48" y="86" width="4" height="14" rx="1" fill="#f5df19" />
      <rect x="64" y="86" width="4" height="12" rx="1" fill="#94a3b8" />
      <rect x="2" y="32" width="12" height="4" rx="1" fill="#94a3b8" />
      <rect x="0" y="48" width="14" height="4" rx="1" fill="#f5df19" />
      <rect x="2" y="64" width="12" height="4" rx="1" fill="#94a3b8" />
      <rect x="86" y="32" width="12" height="4" rx="1" fill="#94a3b8" />
      <rect x="86" y="48" width="14" height="4" rx="1" fill="#f5df19" />
      <rect x="86" y="64" width="12" height="4" rx="1" fill="#94a3b8" />
      <rect x="12" y="12" width="76" height="76" rx="8" fill="url(#chipBodyGradient)" stroke="#1e293b" strokeWidth="2" />
      <rect x="18" y="18" width="64" height="64" rx="6" fill="none" stroke="#f5df19" strokeWidth="0.5" opacity="0.3" />
      <rect x="28" y="28" width="44" height="44" rx="4" fill="#1e293b" opacity="0.5" />
      <text
        x="50"
        y="52"
        fontFamily="system-ui, sans-serif"
        fontSize="42"
        fontWeight="900"
        fill="#f5df19"
        textAnchor="middle"
        dominantBaseline="central"
        filter="url(#chipGlow)"
        style={{ letterSpacing: '-0.02em' }}
      >
        AI
      </text>
      <circle cx="18" cy="18" r="1.5" fill="#f5df19" opacity="0.5" />
      <circle cx="82" cy="18" r="1.5" fill="#f5df19" opacity="0.5" />
      <circle cx="18" cy="82" r="1.5" fill="#f5df19" opacity="0.5" />
      <circle cx="82" cy="82" r="1.5" fill="#f5df19" opacity="0.5" />
    </svg>
  );
}
