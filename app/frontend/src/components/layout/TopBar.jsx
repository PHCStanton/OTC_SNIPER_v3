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
  ChartSpline,
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
  Play,
  Pause,
  Menu,
  X,
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
  const [showTradingDropdown, setShowTradingDropdown] = useState(false);
  const [showGhostDropdown, setShowGhostDropdown] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const { 
    aiDevMode, 
    setAiDevMode, 
    oteoAiEnabled,
    autoGhostEnabled,
    setAutoGhostEnabled,
  } = useSettingsStore();
  const dropdownRef = useRef(null);
  const settingsDropdownRef = useRef(null);
  const notificationsDropdownRef = useRef(null);
  const tradingDropdownRef = useRef(null);
  const ghostDropdownRef = useRef(null);
  const mobileMenuRef = useRef(null);

  const { notifications, markAllAsRead, clearAll } = useNotificationStore();
  const unreadCount = notifications.filter((n) => n.unread).length;
  const [showNotifications, setShowNotifications] = useState(false);
  const [playingNotifId, setPlayingNotifId] = useState(null);
  const currentNotifAudioRef = useRef(null);

  async function playNotifVoice(notif) {
    if (!notif || !(notif.type === 'ai_pulse' || notif.type === 'ai_advisory')) return;
    if (playingNotifId === notif.id) {
      if (currentNotifAudioRef.current) {
        currentNotifAudioRef.current.pause();
        currentNotifAudioRef.current = null;
      }
      setPlayingNotifId(null);
      return;
    }
    const { activeAiProfile, aiProfiles } = useSettingsStore.getState();
    const prof = (aiProfiles || {})[activeAiProfile] || {};
    const v = prof.voice || {};
    const useGrok = v.provider === 'grok';
    const text = notif.message || '';
    if (!text) return;
    setPlayingNotifId(notif.id);
    try {
      if (useGrok) {
        const voiceId = v.voiceId || v.customVoiceId || 'rex';
        const speed = v.speed ?? 1.0;
        const language = v.language || 'en';
        const res = await fetch('/api/ai/speak', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, voice_id: voiceId, language, speed, profile_key: activeAiProfile }),
        });
        if (!res.ok) throw new Error('TTS');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        currentNotifAudioRef.current = audio;
        audio.onended = () => {
          URL.revokeObjectURL(url);
          currentNotifAudioRef.current = null;
          setPlayingNotifId(null);
        };
        audio.onerror = () => {
          URL.revokeObjectURL(url);
          currentNotifAudioRef.current = null;
          setPlayingNotifId(null);
        };
        await audio.play();
      } else {
        if (window.speechSynthesis) {
          window.speechSynthesis.cancel();
          const ut = new SpeechSynthesisUtterance(text);
          ut.onend = () => setPlayingNotifId(null);
          setPlayingNotifId(notif.id);
          window.speechSynthesis.speak(ut);
        } else {
          setPlayingNotifId(null);
        }
      }
    } catch (e) {
      console.warn('Notif voice failed, browser fallback', e);
      if (window.speechSynthesis) {
        const ut = new SpeechSynthesisUtterance(text);
        ut.onend = () => setPlayingNotifId(null);
        window.speechSynthesis.speak(ut);
      }
      setPlayingNotifId(null);
    }
  }

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
      if (tradingDropdownRef.current && !tradingDropdownRef.current.contains(event.target)) {
        setShowTradingDropdown(false);
      }
      if (ghostDropdownRef.current && !ghostDropdownRef.current.contains(event.target)) {
        setShowGhostDropdown(false);
      }
      if (mobileMenuRef.current && !mobileMenuRef.current.contains(event.target)) {
        setShowMobileMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    return () => {
      if (currentNotifAudioRef.current) {
        currentNotifAudioRef.current.pause();
        currentNotifAudioRef.current = null;
      }
      if (window.speechSynthesis) window.speechSynthesis.cancel();
    };
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

  return (
    <>
      <header className="relative flex h-16 items-center justify-between border-b border-white/5 bg-[#1a1c22] px-4 md:px-6 shadow-xl shrink-0 z-50">
        {/* ── Left: Logo + Connections ── */}
        <div className="flex items-center gap-2 md:gap-3">
          <img src={logoImg} alt="OTC SNIPER" className="h-10 md:h-12 lg:h-15 w-auto select-none" draggable={false} />
          <div className="flex items-center gap-2 md:gap-3 ml-1 md:ml-3">
            <button
              onClick={handleChromeToggle}
              disabled={chromeLoading}
              title={chromeRunning ? 'Chrome running — click to stop' : 'Chrome stopped — click to start'}
              className={`hidden sm:flex items-center gap-2 rounded-lg border px-3 py-1.5 md:px-3.5 md:py-2 text-[10px] font-black uppercase tracking-widest select-none transition-all duration-300 ${
                chromeRunning 
                  ? 'border-[#ffb800]/30 bg-[#ffb800]/10 text-[#ffb800] hover:bg-[#ffb800]/20' 
                  : 'border-white/5 bg-[#25282f]/30 text-gray-500 hover:bg-[#25282f]'
              }`}
            >
              {chromeLoading ? <Loader2 size={12} className="animate-spin" /> : <Chrome size={12} />}
              <span>Chrome</span>
              <span className={`h-1.5 w-1.5 rounded-full ${chromeRunning ? 'bg-[#ffb800]' : 'bg-gray-600'}`} />
            </button>
 
            {/* Session Button (ONLY SHOW ONLINE / OFFLINE) */}
            <button
              onClick={() => setShowConnect(true)}
              title={sessionConnected ? 'Session connected — click to manage' : 'No session — click to connect'}
              className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 md:px-3.5 md:py-2 text-[10px] font-black uppercase tracking-widest select-none transition-all duration-300 ${
                sessionConnected 
                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20' 
                  : 'border-white/5 bg-[#25282f]/30 text-gray-500 hover:bg-[#25282f]'
              }`}
            >
              {sessionConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
              <span>{sessionConnected ? 'Online' : 'Offline'}</span>
              <ChevronDown size={10} className="text-gray-500" />
            </button>
          </div>
        </div>
 
        {/* ── Right: Tabs menu + Settings + Profile + Hamburger ── */}
        <div className="flex items-center gap-2 sm:gap-3 md:gap-5">
          {/* Desktop Navigation Group (Visible on lg+ screens) */}
          <div className="hidden lg:flex items-center gap-2 rounded-lg p-0.5">
            {/* Ghost Protocol Dropdown (Ghost Icon) */}
            <div className="relative" ref={ghostDropdownRef}>
              <TopBarIconButton
                onClick={() => setShowGhostDropdown(!showGhostDropdown)}
                title="Ghost Protocol Menu"
                ariaLabel="Open Ghost Protocol menu"
                active={activeView === 'journal' || (activeView === 'settings' && activeSettingsTab === 'ghost') || showGhostDropdown}
              >
                <Ghost size={22} strokeWidth={2} />
              </TopBarIconButton>

              {showGhostDropdown && (
                <div className="absolute right-0 mt-2 w-60 rounded-xl border border-white/10 bg-[#161920] p-2 shadow-2xl z-[100] space-y-1 text-left">
                  <div className="border-b border-white/5 px-2 pb-1.5 pt-0.5 mb-1">
                    <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">Ghost Protocol</span>
                  </div>

                  <button
                    onClick={() => {
                      setAutoGhostEnabled(!autoGhostEnabled);
                      setShowGhostDropdown(false);
                    }}
                    className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs font-bold transition duration-300 ${
                      autoGhostEnabled
                        ? 'bg-[#ffb800]/15 text-[#ffb800] border border-[#ffb800]/25'
                        : 'text-gray-300 hover:bg-[#ffb800]/10 hover:text-[#ffb800] border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Zap size={14} className={autoGhostEnabled ? 'text-[#ffb800]' : 'text-gray-400'} />
                      <div className="flex flex-col">
                        <span>Ghost Protocol</span>
                        <span className="text-[8px] text-gray-500 font-semibold tracking-normal uppercase">Simulated trade automation</span>
                      </div>
                    </div>
                    <div className={`h-2.5 w-2.5 rounded-full ${autoGhostEnabled ? 'bg-[#ffb800] animate-pulse' : 'bg-gray-600'}`} />
                  </button>

                  <button
                    onClick={() => {
                      setActiveSettingsTab('ghost');
                      setActiveView('settings');
                      setShowGhostDropdown(false);
                    }}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-xs font-bold transition duration-300 ${
                      activeView === 'settings' && activeSettingsTab === 'ghost'
                        ? 'bg-[#ffb800]/15 text-[#ffb800] border border-[#ffb800]/25'
                        : 'text-gray-300 hover:bg-[#ffb800]/10 hover:text-[#ffb800] border border-transparent'
                    }`}
                  >
                    <Ghost size={14} className={activeView === 'settings' && activeSettingsTab === 'ghost' ? 'text-[#ffb800]' : 'text-gray-400'} />
                    <div className="flex flex-col">
                      <span>Auto-Ghost Settings</span>
                      <span className="text-[8px] text-gray-500 font-semibold tracking-normal uppercase">Configure gates, blacklist & sizing</span>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      setActiveView('journal');
                      setShowGhostDropdown(false);
                    }}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-xs font-bold transition duration-300 ${
                      activeView === 'journal'
                        ? 'bg-[#ffb800]/15 text-[#ffb800] border border-[#ffb800]/25'
                        : 'text-gray-300 hover:bg-[#ffb800]/10 hover:text-[#ffb800] border border-transparent'
                    }`}
                  >
                    <BookOpen size={14} className={activeView === 'journal' ? 'text-[#ffb800]' : 'text-gray-400'} />
                    <div className="flex flex-col">
                      <span>Ghost Journal</span>
                      <span className="text-[8px] text-gray-500 font-semibold tracking-normal uppercase">Simulated trade history logs</span>
                    </div>
                  </button>
                </div>
              )}
            </div>

            {/* Trading Portal Dropdown (ChartSpline) */}
            <div className="relative" ref={tradingDropdownRef}>
              <TopBarIconButton
                onClick={() => setShowTradingDropdown(!showTradingDropdown)}
                title="Trading Portal"
                ariaLabel="Open trading menu"
                active={isTrading || isRisk || showTradingDropdown}
              >
                <ChartSpline size={22} strokeWidth={2} />
              </TopBarIconButton>

              {showTradingDropdown && (
                <div className="absolute right-0 mt-2 w-56 rounded-xl border border-white/10 bg-[#161920] p-2 shadow-2xl z-[100] space-y-1 text-left">
                  <div className="border-b border-white/5 px-2 pb-1.5 pt-0.5 mb-1">
                    <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">Trading Portal</span>
                  </div>

                  <button
                    onClick={() => {
                      setActiveView('trading');
                      setDashboardMode('trading');
                      setShowTradingDropdown(false);
                      setTimeout(() => {
                        const el = document.getElementById('multi-chart-view-section');
                        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                      }, 100);
                    }}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-xs font-bold transition duration-300 ${
                      isTrading
                        ? 'bg-[#ffb800]/15 text-[#ffb800] border border-[#ffb800]/25'
                        : 'text-gray-300 hover:bg-[#ffb800]/10 hover:text-[#ffb800] border border-transparent'
                    }`}
                  >
                    <LayoutGrid size={14} className={isTrading ? 'text-[#ffb800]' : 'text-gray-400'} />
                    <div className="flex flex-col">
                      <span>Multi-Chart Grid</span>
                      <span className="text-[8px] text-gray-500 font-semibold tracking-normal uppercase">Watch multiple asset OTC charts</span>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      setActiveView('trading');
                      setDashboardMode('trading');
                      setShowTradingDropdown(false);
                      setTimeout(() => {
                        const el = document.getElementById('sparkline-section');
                        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                      }, 100);
                    }}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-xs font-bold transition duration-300 ${
                      isTrading
                        ? 'bg-[#ffb800]/15 text-[#ffb800] border border-[#ffb800]/25'
                        : 'text-gray-300 hover:bg-[#ffb800]/10 hover:text-[#ffb800] border border-transparent'
                    }`}
                  >
                    <ChartSpline size={14} className={isTrading ? 'text-[#ffb800]' : 'text-gray-400'} />
                    <div className="flex flex-col">
                      <span>Sparkline Focus</span>
                      <span className="text-[8px] text-gray-500 font-semibold tracking-normal uppercase">Detailed single-chart analyzer</span>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      setActiveView('risk');
                      setDashboardMode('risk');
                      setShowTradingDropdown(false);
                    }}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-xs font-bold transition duration-300 ${
                      isRisk
                        ? 'bg-[#ffb800]/15 text-[#ffb800] border border-[#ffb800]/25'
                        : 'text-gray-300 hover:bg-[#ffb800]/10 hover:text-[#ffb800] border border-transparent'
                    }`}
                  >
                    <ShieldAlert size={14} className={isRisk ? 'text-[#ffb800]' : 'text-gray-400'} />
                    <div className="flex flex-col">
                      <span>Risk Dashboard</span>
                      <span className="text-[8px] text-gray-500 font-semibold tracking-normal uppercase">Sizing, balance & daily limits</span>
                    </div>
                  </button>
                </div>
              )}
            </div>
            
            {/* Settings Dropdown Portal */}
            <div className="relative ml-1" ref={settingsDropdownRef}>
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
                      <span className="text-[8px] text-gray-500 font-semibold tracking-normal uppercase">OTEO, UI Prefs</span>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      setActiveSettingsTab('ghost');
                      setActiveView('settings');
                      setShowSettingsDropdown(false);
                    }}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-xs font-bold transition duration-300 ${
                      isSettings && activeSettingsTab === 'ghost'
                        ? 'bg-[#ffb800]/15 text-[#ffb800] border border-[#ffb800]/25'
                        : 'text-gray-300 hover:bg-[#ffb800]/10 hover:text-[#ffb800] border border-transparent'
                    }`}
                  >
                    <Ghost size={14} className={isSettings && activeSettingsTab === 'ghost' ? 'text-[#ffb800]' : 'text-gray-400'} />
                    <div className="flex flex-col">
                      <span>Ghost Protocol</span>
                      <span className="text-[8px] text-gray-500 font-semibold tracking-normal uppercase">Protocol, Gates, Blacklist</span>
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
          </div>
 
          {/* Utility Right Group */}
          <div className="flex items-center gap-2 sm:gap-3 lg:border-l lg:border-white/5 lg:pl-4">
            {/* AI Assistant Menu */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setShowAiDropdown(!showAiDropdown)}
                title="AI Assistant Menu"
                className={`flex h-9 w-9 sm:h-10 sm:w-10 md:h-11 md:w-11 items-center justify-center rounded-lg border transition-all duration-350 ${
                  isAI || showAiDropdown
                    ? 'border-[#ffb800]/40 bg-[#ffb800]/10 shadow-[0_0_15px_rgba(255,184,0,0.12)] scale-105' 
                    : 'border-transparent bg-transparent hover:bg-white/5 grayscale hover:grayscale-0'
                }`}
              >
                <AiChipIcon size={34} />
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
 
            {/* Profile Avatar (Desktop/Tablet) */}
            <button
              type="button"
              className="hidden sm:flex h-9 w-9 sm:h-10 sm:w-10 md:h-11 md:w-11 items-center justify-center rounded-full border border-white/5 bg-[#25282f]/50 p-0.5 transition hover:border-[#ffb800]/30 hover:bg-[#2d3139]"
              title="Profile"
            >
              <img
                src="/Sci-fi_GUY.jpg"
                alt="Profile"
                className="h-8 w-8 sm:h-9 sm:w-9 rounded-full object-cover"
              />
            </button>
 
            {/* Balance Pill (Desktop/Tablet) */}
            <div className="hidden sm:flex h-9 sm:h-10 md:h-11 min-w-[130px] md:min-w-[160px] items-center gap-2 md:gap-3 rounded-lg border border-white/5 bg-[#25282f]/30 px-3 md:px-4">
              <div className="flex h-5 w-5 md:h-6 md:w-6 items-center justify-center rounded-md bg-[#ffb800]/10 text-[#ffb800]">
                <DollarSign size={12} />
              </div>
              <span className="text-xs md:text-md font-black tracking-tight text-white">{balanceLabel}</span>
            </div>
 
            {/* Notifications Bell */}
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
                            {(n.type === 'ai_pulse' || n.type === 'ai_advisory') && (
                              <button
                                onClick={(e) => { e.stopPropagation(); playNotifVoice(n); }}
                                className="ml-1 shrink-0 text-[#ffb800] hover:text-white p-0.5 rounded hover:bg-white/10"
                                title={playingNotifId === n.id ? 'Stop voice readback' : 'Read back advisory with Grok voice'}
                              >
                                {playingNotifId === n.id ? <Pause size={13} /> : <Play size={13} />}
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* ── Mobile & Tablet Hamburger Toggle (Visible on < lg) ── */}
            <div className="relative lg:hidden" ref={mobileMenuRef}>
              <button
                type="button"
                onClick={() => setShowMobileMenu(!showMobileMenu)}
                title="Main Navigation Menu"
                aria-label="Toggle navigation menu"
                className={`flex h-9 w-9 sm:h-10 sm:w-10 md:h-11 md:w-11 items-center justify-center rounded-lg border transition-all duration-300 ${
                  showMobileMenu
                    ? 'border-[#ffb800]/40 bg-[#ffb800]/15 text-[#ffb800] shadow-[0_0_12px_rgba(255,184,0,0.15)]'
                    : 'border-white/10 bg-[#25282f]/50 text-gray-300 hover:border-[#ffb800]/30 hover:bg-[#2d3139] hover:text-white'
                }`}
              >
                {showMobileMenu ? <X size={20} /> : <Menu size={20} />}
              </button>

              {/* Responsive Hamburger Drawer Menu */}
              {showMobileMenu && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 max-h-[calc(100vh-80px)] overflow-y-auto rounded-2xl border border-white/10 bg-[#161920]/95 backdrop-blur-xl p-4 shadow-2xl z-[150] space-y-4 text-left scrollbar-thin animate-in fade-in slide-in-from-top-2 duration-200">
                  {/* Balance & Status Banner for mobile */}
                  <div className="flex items-center justify-between rounded-xl bg-[#1a1c22] border border-white/5 p-3">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#ffb800]/10 text-[#ffb800] border border-[#ffb800]/20">
                        <DollarSign size={16} />
                      </div>
                      <div>
                        <span className="text-[9px] font-black uppercase tracking-widest text-gray-500 block">Current Balance</span>
                        <span className="text-sm font-black text-white font-mono">{balanceLabel}</span>
                      </div>
                    </div>
                    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-[8px] font-black tracking-widest uppercase border ${
                      sessionConnected ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-white/5 bg-[#25282f] text-gray-500'
                    }`}>
                      {sessionConnected ? <Wifi size={10} /> : <WifiOff size={10} />}
                      {sessionConnected ? (accountType ? accountType.toUpperCase() : 'ONLINE') : 'OFFLINE'}
                    </span>
                  </div>

                  {/* Ghost Protocol Navigation */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between px-1">
                      <span className="text-[10px] font-black uppercase tracking-widest text-[#ffb800] flex items-center gap-1.5">
                        <Ghost size={12} /> Ghost Protocol
                      </span>
                    </div>

                    <button
                      onClick={() => {
                        setAutoGhostEnabled(!autoGhostEnabled);
                        setShowMobileMenu(false);
                      }}
                      className={`flex w-full items-center justify-between rounded-xl p-2.5 text-xs font-bold transition duration-300 ${
                        autoGhostEnabled
                          ? 'bg-[#ffb800]/15 text-[#ffb800] border border-[#ffb800]/30'
                          : 'bg-[#1a1c22] text-gray-300 hover:bg-[#25282f] border border-white/5'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <Zap size={14} className={autoGhostEnabled ? 'text-[#ffb800]' : 'text-gray-400'} />
                        <div className="flex flex-col text-left">
                          <span>Auto-Ghost Automation</span>
                          <span className="text-[8px] text-gray-500 uppercase font-semibold">Simulated execution state</span>
                        </div>
                      </div>
                      <div className={`h-2.5 w-2.5 rounded-full ${autoGhostEnabled ? 'bg-[#ffb800] animate-pulse' : 'bg-gray-600'}`} />
                    </button>

                    <button
                      onClick={() => {
                        setActiveSettingsTab('ghost');
                        setActiveView('settings');
                        setShowMobileMenu(false);
                      }}
                      className={`flex w-full items-center gap-2.5 rounded-xl p-2.5 text-xs font-bold transition bg-[#1a1c22] border border-white/5 hover:border-[#ffb800]/30 ${
                        activeView === 'settings' && activeSettingsTab === 'ghost' ? 'text-[#ffb800] bg-[#ffb800]/10 border-[#ffb800]/30' : 'text-gray-300'
                      }`}
                    >
                      <Ghost size={14} className="text-[#ffb800]" />
                      <div className="flex flex-col text-left">
                        <span>Ghost Protocol Settings</span>
                        <span className="text-[8px] text-gray-500 uppercase font-semibold">Configure gates, blacklist & sizing</span>
                      </div>
                    </button>

                    <button
                      onClick={() => {
                        setActiveView('journal');
                        setShowMobileMenu(false);
                      }}
                      className={`flex w-full items-center gap-2.5 rounded-xl p-2.5 text-xs font-bold transition bg-[#1a1c22] border border-white/5 hover:border-[#ffb800]/30 ${
                        activeView === 'journal' ? 'text-[#ffb800] bg-[#ffb800]/10 border-[#ffb800]/30' : 'text-gray-300'
                      }`}
                    >
                      <BookOpen size={14} className="text-amber-400" />
                      <div className="flex flex-col text-left">
                        <span>Ghost Journal</span>
                        <span className="text-[8px] text-gray-500 uppercase font-semibold">Simulated trade history logs</span>
                      </div>
                    </button>
                  </div>

                  {/* Trading Portal Navigation */}
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-black uppercase tracking-widest text-[#ffb800] px-1 flex items-center gap-1.5">
                      <ChartSpline size={12} /> Trading Portal
                    </span>

                    <button
                      onClick={() => {
                        setActiveView('trading');
                        setDashboardMode('trading');
                        setShowMobileMenu(false);
                      }}
                      className={`flex w-full items-center gap-2.5 rounded-xl p-2.5 text-xs font-bold transition bg-[#1a1c22] border border-white/5 hover:border-[#ffb800]/30 ${
                        isTrading ? 'text-[#ffb800] bg-[#ffb800]/10 border-[#ffb800]/30' : 'text-gray-300'
                      }`}
                    >
                      <LayoutGrid size={14} className="text-sky-400" />
                      <div className="flex flex-col text-left">
                        <span>Multi-Chart Grid</span>
                        <span className="text-[8px] text-gray-500 uppercase font-semibold">Watchlist & live sparklines</span>
                      </div>
                    </button>

                    <button
                      onClick={() => {
                        setActiveView('risk');
                        setDashboardMode('risk');
                        setShowMobileMenu(false);
                      }}
                      className={`flex w-full items-center gap-2.5 rounded-xl p-2.5 text-xs font-bold transition bg-[#1a1c22] border border-white/5 hover:border-[#ffb800]/30 ${
                        isRisk ? 'text-[#ffb800] bg-[#ffb800]/10 border-[#ffb800]/30' : 'text-gray-300'
                      }`}
                    >
                      <ShieldAlert size={14} className="text-rose-400" />
                      <div className="flex flex-col text-left">
                        <span>Risk Dashboard</span>
                        <span className="text-[8px] text-gray-500 uppercase font-semibold">Sizing, balance & guardrails</span>
                      </div>
                    </button>
                  </div>

                  {/* Settings Portal Navigation */}
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-black uppercase tracking-widest text-[#ffb800] px-1 flex items-center gap-1.5">
                      <Settings size={12} /> Settings Portal
                    </span>

                    <div className="grid grid-cols-2 gap-1.5">
                      <button
                        onClick={() => {
                          setActiveSettingsTab('account');
                          setActiveView('settings');
                          setShowMobileMenu(false);
                        }}
                        className={`flex items-center gap-2 rounded-lg p-2 text-xs font-bold transition bg-[#1a1c22] border border-white/5 ${
                          isSettings && activeSettingsTab === 'account' ? 'text-[#ffb800] border-[#ffb800]/30 bg-[#ffb800]/10' : 'text-gray-300'
                        }`}
                      >
                        <UserRound size={12} className="text-gray-400" /> Account
                      </button>
                      <button
                        onClick={() => {
                          setActiveSettingsTab('app');
                          setActiveView('settings');
                          setShowMobileMenu(false);
                        }}
                        className={`flex items-center gap-2 rounded-lg p-2 text-xs font-bold transition bg-[#1a1c22] border border-white/5 ${
                          isSettings && activeSettingsTab === 'app' ? 'text-[#ffb800] border-[#ffb800]/30 bg-[#ffb800]/10' : 'text-gray-300'
                        }`}
                      >
                        <LayoutGrid size={12} className="text-gray-400" /> App Prefs
                      </button>
                      <button
                        onClick={() => {
                          setActiveSettingsTab('ai');
                          setActiveView('settings');
                          setShowMobileMenu(false);
                        }}
                        className={`flex items-center gap-2 rounded-lg p-2 text-xs font-bold transition bg-[#1a1c22] border border-white/5 ${
                          isSettings && activeSettingsTab === 'ai' ? 'text-[#ffb800] border-[#ffb800]/30 bg-[#ffb800]/10' : 'text-gray-300'
                        }`}
                      >
                        <Zap size={12} className="text-gray-400" /> AI Config
                      </button>
                      <button
                        onClick={() => {
                          setActiveSettingsTab('risk');
                          setActiveView('settings');
                          setShowMobileMenu(false);
                        }}
                        className={`flex items-center gap-2 rounded-lg p-2 text-xs font-bold transition bg-[#1a1c22] border border-white/5 ${
                          isSettings && activeSettingsTab === 'risk' ? 'text-[#ffb800] border-[#ffb800]/30 bg-[#ffb800]/10' : 'text-gray-300'
                        }`}
                      >
                        <ShieldAlert size={12} className="text-gray-400" /> Risk Limits
                      </button>
                    </div>
                  </div>

                  {/* AI Assistant Quick Actions */}
                  <div className="space-y-1.5 pt-1 border-t border-white/5">
                    <span className="text-[10px] font-black uppercase tracking-widest text-[#ffb800] px-1 flex items-center gap-1.5">
                      <Bot size={12} /> AI Advisory
                    </span>
                    <div className="grid grid-cols-2 gap-1.5">
                      <button
                        onClick={() => {
                          setActiveView('ai');
                          setShowMobileMenu(false);
                        }}
                        className="flex items-center gap-2 rounded-lg p-2 text-xs font-bold text-gray-300 bg-[#1a1c22] border border-white/5 hover:text-white"
                      >
                        <Bot size={12} className="text-[#ffb800]" /> Open Chat
                      </button>
                      <button
                        onClick={() => {
                          setActiveView('analysis');
                          setShowMobileMenu(false);
                        }}
                        className="flex items-center gap-2 rounded-lg p-2 text-xs font-bold text-gray-300 bg-[#1a1c22] border border-white/5 hover:text-white"
                      >
                        <TrendingUp size={12} className="text-emerald-400" /> Analytics
                      </button>
                    </div>
                  </div>
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
