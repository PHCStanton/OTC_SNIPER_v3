/**
 * TopBar — Chrome badge + SSID/Session badge + Theme toggle + Tab toggle.
 * Driven by useOpsStore (live status from Socket.IO check_status polling).
 */
import { useState, useRef, useEffect } from 'react';
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
  Bot,
  Zap,
  Save,
} from 'lucide-react';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { useLayoutStore } from '../../stores/useLayoutStore.js';
import { useToastStore } from '../../stores/useToastStore.js';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useAIStore } from '../../stores/useAIStore.js';
import { chromeStart, chromeStop } from '../../api/opsApi.js';
import ConnectDialog from '../auth/ConnectDialog.jsx';
import logoImg from '../../../assets/GOLD_TARGET_LOGO1_RM.png';

export default function TopBar() {
  const { chromeStatus, sessionStatus, balance, accountType, setChromeStatus } = useOpsStore();
  const { activeView, dashboardMode, setDashboardMode, setActiveView } = useLayoutStore();
  const [showConnect, setShowConnect] = useState(false);
  const [chromeLoading, setChromeLoading] = useState(false);
  const [showAiDropdown, setShowAiDropdown] = useState(false);
  const { aiDevMode, setAiDevMode } = useSettingsStore();
  const dropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowAiDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
 
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setShowAiDropdown(!showAiDropdown)}
                title="AI Assistant Menu"
                className={`ml-2 flex h-11 w-11 items-center justify-center rounded-lg border transition-all duration-350 ${
                  isAI || showAiDropdown
                    ? 'border-[#ffb800]/40 bg-[#ffb800]/10 shadow-[0_0_15px_rgba(255,184,0,0.12)] scale-105' 
                    : 'border-transparent bg-transparent hover:bg-white/5 grayscale hover:grayscale-0'
                }`}
              >
                <AiChipIcon size={38} />
              </button>
              {showAiDropdown && (
                <div className="absolute right-0 mt-2 w-64 rounded-xl border border-white/5 bg-[#1a1c22] p-3 shadow-2xl z-[100] space-y-3 text-left">
                  <div className="flex items-center justify-between border-b border-white/5 pb-2">
                    <span className="text-[10px] font-black uppercase tracking-widest text-[#ffb800]">AI Assistant Menu</span>
                    <span className="text-[9px] font-bold text-gray-500">v3.0</span>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <button
                      onClick={() => {
                        setActiveView('ai');
                        setShowAiDropdown(false);
                      }}
                      className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-gray-300 hover:bg-white/5 hover:text-white transition"
                    >
                      <Bot size={14} className="text-[#ffb800]" />
                      <span>Open AI Chat</span>
                    </button>

                    <div className="flex items-center justify-between rounded-lg bg-white/[0.02] border border-white/5 p-2.5">
                      <div className="flex flex-col text-left">
                        <span className="text-[10px] font-black uppercase tracking-wide text-white">Developer Mode</span>
                        <span className="text-[8px] text-gray-500">Discuss platform upgrades</span>
                      </div>
                      <button
                        onClick={() => setAiDevMode(!aiDevMode)}
                        className={`h-4 w-8 rounded-full transition-colors ${aiDevMode ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
                      >
                        <div className={`h-2.5 w-2.5 rounded-full bg-white transition-transform ${aiDevMode ? 'translate-x-4' : 'translate-x-0.5'}`} />
                      </button>
                    </div>

                    <button
                      onClick={() => {
                        useToastStore.getState().addToast({ type: 'info', message: '[AI Advisor] Analyzing trade results (placeholder)' });
                        setShowAiDropdown(false);
                      }}
                      className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-gray-400 hover:bg-white/5 hover:text-white transition"
                    >
                      <TrendingUp size={14} />
                      <span>Analyze Trade Results</span>
                    </button>

                    <button
                      onClick={() => {
                        useToastStore.getState().addToast({ type: 'success', message: '[AI Advisor] Attached active session context' });
                        setShowAiDropdown(false);
                      }}
                      className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-gray-400 hover:bg-white/5 hover:text-white transition"
                    >
                      <Save size={14} />
                      <span>Upload Active Context</span>
                    </button>

                    {aiDevMode && (
                      <button
                        onClick={() => {
                          useAIStore.getState().setDraft("Grok, what features should we add to OTC SNIPER to increase the quality of AI outputs and trading performance?");
                          setActiveView('ai');
                          setShowAiDropdown(false);
                        }}
                        className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-emerald-400 hover:bg-white/5 hover:text-emerald-300 transition"
                      >
                        <Zap size={14} />
                        <span>Platform Quality Insights</span>
                      </button>
                    )}

                    <button
                      onClick={() => {
                        setActiveView('journal');
                        setShowAiDropdown(false);
                      }}
                      className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-gray-400 hover:bg-white/5 hover:text-white transition"
                    >
                      <BookOpen size={14} />
                      <span>Open Trading Journal</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
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

export function AiChipIcon({ size = 16 }) {
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
