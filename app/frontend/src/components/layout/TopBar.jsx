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
  UserRound,
  LayoutGrid,
} from 'lucide-react';
import { useOpsStore } from '../../stores/useOpsStore.js';
import { useLayoutStore } from '../../stores/useLayoutStore.js';
import { useToastStore } from '../../stores/useToastStore.js';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useAIStore } from '../../stores/useAIStore.js';
import { useNotificationStore } from '../../stores/useNotificationStore.js';
import { chromeStart, chromeStop } from '../../api/opsApi.js';
import ConnectDialog from '../auth/ConnectDialog.jsx';
import logoImg from '../../../assets/GOLD_TARGET_LOGO1_RM.png';

export default function TopBar() {
  const { chromeStatus, sessionStatus, balance, accountType, setChromeStatus } = useOpsStore();
  const { 
    activeView, 
    dashboardMode, 
    setDashboardMode, 
    setActiveView,
    activeSettingsTab,
    setActiveSettingsTab,
  } = useLayoutStore();
  const [showConnect, setShowConnect] = useState(false);
  const [chromeLoading, setChromeLoading] = useState(false);
  const [showAiDropdown, setShowAiDropdown] = useState(false);
  const [showSettingsDropdown, setShowSettingsDropdown] = useState(false);
  const { 
    aiDevMode, 
    setAiDevMode, 
    oteoAiEnabled,
  } = useSettingsStore();
  const dropdownRef = useRef(null);
  const settingsDropdownRef = useRef(null);
  const notificationsDropdownRef = useRef(null);

  const { notifications, markAllAsRead, clearAll } = useNotificationStore();
  const unreadCount = notifications.filter((n) => n.unread).length;
  const [showNotifications, setShowNotifications] = useState(false);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowAiDropdown(false);
      }
      if (settingsDropdownRef.current && !settingsDropdownRef.current.contains(event.target)) {
        setShowSettingsDropdown(false);
      }
      if (notificationsDropdownRef.current && !notificationsDropdownRef.current.contains(event.target)) {
        setShowNotifications(false);
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

  // Deprecated notifications placeholder removed in favor of real store connection

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
                <div className="absolute right-0 mt-2 w-80 rounded-xl border-2 border-[#1a1c22] bg-gradient-to-br from-[#f5df19] to-[#ffb800] p-3 shadow-[0_10px_30px_rgba(245,223,25,0.25)] z-[100] space-y-3 text-left">
                  <div className="flex items-center justify-between border-b border-black/10 pb-2">
                    <span className="text-[10px] font-black uppercase tracking-widest text-[#1a1c22]">AI Assistant Menu</span>
                    {oteoAiEnabled ? (
                      <span className="rounded bg-black/10 px-1.5 py-0.5 text-[8px] font-black uppercase tracking-wider text-[#1a1c22] border border-black/10">
                        Active Advisor
                      </span>
                    ) : (
                      <span className="rounded bg-black/10 px-1.5 py-0.5 text-[8px] font-black uppercase tracking-wider text-black/50 border border-black/10">
                        Inactive
                      </span>
                    )}
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <button
                      onClick={() => {
                        setActiveView('ai');
                        setShowAiDropdown(false);
                      }}
                      className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-gray-300 bg-[#1a1c22] hover:bg-[#25282f] hover:text-white transition border border-white/5"
                    >
                      <Bot size={14} className="text-[#ffb800]" />
                      <span>Open AI Chat</span>
                    </button>

                    <div className="flex items-center justify-between rounded-lg bg-[#1a1c22] border border-white/5 p-2.5">
                      <div className="flex flex-col text-left">
                        <span className="text-[10px] font-black uppercase tracking-wide text-white">Developer Mode</span>
                        <span className="text-[8px] text-gray-500">Discuss platform upgrades</span>
                      </div>
                      <button
                        onClick={() => setAiDevMode(!aiDevMode)}
                        className={`h-4 w-8 rounded-full transition-colors shrink-0 ${aiDevMode ? 'bg-[#ffb800]' : 'bg-[#2d3139]'}`}
                      >
                        <div className={`h-2.5 w-2.5 rounded-full bg-white transition-transform ${aiDevMode ? 'translate-x-4' : 'translate-x-0.5'}`} />
                      </button>
                    </div>

                    {aiDevMode && (
                      <button
                        onClick={() => {
                          useAIStore.getState().setDraft("Grok, what features should we add to OTC SNIPER to increase the quality of AI outputs and trading performance?");
                          setActiveView('ai');
                          setShowAiDropdown(false);
                        }}
                        className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-emerald-400 bg-[#1a1c22] hover:bg-[#25282f] hover:text-emerald-300 transition border border-emerald-500/10"
                      >
                        <Zap size={14} />
                        <span>Platform Quality Insights</span>
                      </button>
                    )}

                    <button
                      onClick={() => {
                        setActiveView('analysis');
                        setShowAiDropdown(false);
                      }}
                      className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-gray-300 bg-[#1a1c22] hover:bg-[#25282f] hover:text-white transition border border-white/5"
                    >
                      <TrendingUp size={14} />
                      <span>Analyze Trade Results</span>
                    </button>

                    <button
                      onClick={() => {
                        setActiveView('journal');
                        setShowAiDropdown(false);
                      }}
                      className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-gray-400 bg-[#1a1c22] hover:bg-[#25282f] hover:text-white transition border border-white/5"
                    >
                      <BookOpen size={14} />
                      <span>Open Trading Journal</span>
                    </button>

                    <button
                      onClick={() => {
                        useToastStore.getState().addToast({ type: 'success', message: '[AI Advisor] Attached active session context' });
                        setShowAiDropdown(false);
                      }}
                      className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-gray-400 bg-[#1a1c22] hover:bg-[#25282f] hover:text-white transition border border-white/5"
                    >
                      <Save size={14} />
                      <span>Upload Active Context</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
 
          <div className="flex items-center gap-2 border-l border-white/5 pl-4">
            <div className="relative" ref={settingsDropdownRef}>
              <TopBarIconButton
                onClick={() => setShowSettingsDropdown(!showSettingsDropdown)}
                title="Settings"
                ariaLabel="Open settings"
                active={isSettings || showSettingsDropdown}
              >
                <Settings size={22} strokeWidth={2} />
              </TopBarIconButton>

              {showSettingsDropdown && (
                <div className="absolute right-0 mt-2 w-72 rounded-xl border border-white/10 bg-[#161920] p-2 shadow-2xl z-[100] space-y-1 text-left">
                  <div className="border-b border-white/5 px-2 pb-1.5 pt-0.5 mb-1">
                    <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">Settings Portal</span>
                  </div>
                  
                  <button
                    onClick={() => {
                      setActiveSettingsTab('account');
                      setActiveView('settings');
                      setShowSettingsDropdown(false);
                    }}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-xs font-bold transition duration-300 ${
                      isSettings && activeSettingsTab === 'account'
                        ? 'bg-[#ffb800]/15 text-[#ffb800] border border-[#ffb800]/25'
                        : 'text-gray-300 hover:bg-[#ffb800]/10 hover:text-[#ffb800] border border-transparent'
                    }`}
                  >
                    <UserRound size={14} className={isSettings && activeSettingsTab === 'account' ? 'text-[#ffb800]' : 'text-gray-400'} />
                    <div className="flex flex-col">
                      <span>Account Settings</span>
                      <span className="text-[8px] text-gray-500 font-semibold tracking-normal uppercase">SSID, Broker, Session Identity</span>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      setActiveSettingsTab('app');
                      setActiveView('settings');
                      setShowSettingsDropdown(false);
                    }}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-xs font-bold transition duration-300 ${
                      isSettings && activeSettingsTab === 'app'
                        ? 'bg-[#ffb800]/15 text-[#ffb800] border border-[#ffb800]/25'
                        : 'text-gray-300 hover:bg-[#ffb800]/10 hover:text-[#ffb800] border border-transparent'
                    }`}
                  >
                    <LayoutGrid size={14} className={isSettings && activeSettingsTab === 'app' ? 'text-[#ffb800]' : 'text-gray-400'} />
                    <div className="flex flex-col">
                      <span>App Settings</span>
                      <span className="text-[8px] text-gray-500 font-semibold tracking-normal uppercase">OTEO, Ghost Trading, UI Prefs</span>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      setActiveSettingsTab('ai');
                      setActiveView('settings');
                      setShowSettingsDropdown(false);
                    }}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-xs font-bold transition duration-300 ${
                      isSettings && activeSettingsTab === 'ai'
                        ? 'bg-[#ffb800]/15 text-[#ffb800] border border-[#ffb800]/25'
                        : 'text-gray-300 hover:bg-[#ffb800]/10 hover:text-[#ffb800] border border-transparent'
                    }`}
                  >
                    <Zap size={14} className={isSettings && activeSettingsTab === 'ai' ? 'text-[#ffb800]' : 'text-gray-400'} />
                    <div className="flex flex-col">
                      <span>AI Settings</span>
                      <span className="text-[8px] text-gray-500 font-semibold tracking-normal uppercase">Models, Voices, KB Patterns</span>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      setActiveSettingsTab('risk');
                      setActiveView('settings');
                      setShowSettingsDropdown(false);
                    }}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-xs font-bold transition duration-300 ${
                      isSettings && activeSettingsTab === 'risk'
                        ? 'bg-[#ffb800]/15 text-[#ffb800] border border-[#ffb800]/25'
                        : 'text-gray-300 hover:bg-[#ffb800]/10 hover:text-[#ffb800] border border-transparent'
                    }`}
                  >
                    <ShieldAlert size={14} className={isSettings && activeSettingsTab === 'risk' ? 'text-[#ffb800]' : 'text-gray-400'} />
                    <div className="flex flex-col">
                      <span>Risk Settings</span>
                      <span className="text-[8px] text-gray-500 font-semibold tracking-normal uppercase">Capital, Payout, Sizing, Guardrails</span>
                    </div>
                  </button>
                </div>
              )}
            </div>
 
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
 
            <div className="relative" ref={notificationsDropdownRef}>
              <TopBarIconButton
                onClick={() => {
                  setShowNotifications(!showNotifications);
                  if (!showNotifications) {
                    markAllAsRead();
                  }
                }}
                title="System Notifications"
                ariaLabel="System Notifications"
                active={showNotifications}
              >
                <Bell size={20} strokeWidth={2} />
                {unreadCount > 0 && (
                  <span className="absolute top-1.5 right-1.5 flex h-2.5 w-2.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75"></span>
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500"></span>
                  </span>
                )}
              </TopBarIconButton>

              {showNotifications && (
                <div className="absolute right-0 mt-2 w-80 rounded-xl border border-white/10 bg-[#161920] p-3 shadow-2xl z-[100] text-left">
                  <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-2">
                    <span className="text-[10px] font-black uppercase tracking-widest text-gray-400">AI Notifications</span>
                    <button 
                      onClick={clearAll}
                      className="text-[8px] font-black uppercase tracking-widest text-gray-500 hover:text-white transition"
                    >
                      Clear All
                    </button>
                  </div>

                  {notifications.length === 0 ? (
                    <div className="py-6 text-center text-xs font-bold text-gray-600 uppercase italic">
                      No notifications
                    </div>
                  ) : (
                    <div className="space-y-1.5 max-h-[260px] overflow-y-auto pr-0.5 scrollbar-thin">
                      {notifications.map((n) => {
                        const Icon = n.type === 'ai_pulse' ? Zap : Bot;
                        const iconColor = n.type === 'ai_pulse' ? 'text-amber-400' : 'text-[#ffb800]';
                        
                        const elapsedSecs = Math.max(0, Math.floor(Date.now() / 1000 - n.timestamp));
                        let timeStr = 'now';
                        if (elapsedSecs >= 60) {
                          timeStr = `${Math.floor(elapsedSecs / 60)}m ago`;
                        } else if (elapsedSecs > 5) {
                          timeStr = `${elapsedSecs}s ago`;
                        }

                        return (
                          <div
                            key={n.id}
                            className="flex items-start gap-2.5 rounded-lg border p-2.5 transition bg-white/[0.01] border-white/5"
                          >
                            <div className={`mt-0.5 shrink-0 ${iconColor}`}>
                              <Icon size={14} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-[10px] text-gray-300 font-medium leading-relaxed break-words">
                                {n.message}
                              </p>
                              <span className="text-[8px] text-gray-600 font-bold uppercase mt-1 block">
                                {timeStr}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
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
