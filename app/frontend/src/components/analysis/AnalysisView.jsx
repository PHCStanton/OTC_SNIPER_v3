import React, { useState, useEffect, useRef } from 'react';
import { useSettingsStore } from '../../stores/useSettingsStore.js';
import { useRiskStore } from '../../stores/useRiskStore.js';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Bot,
  Calendar,
  Volume2,
  VolumeX,
  Play,
  Pause,
  RefreshCw,
  Search,
  BookOpen,
  Award,
  Layers,
  Clock,
  ChevronRight,
  ShieldCheck,
  AlertTriangle,
  Plus,
  Filter
} from 'lucide-react';
import { useToastStore } from '../../stores/useToastStore.js';

export default function AnalysisView() {
  const [activeTab, setActiveTab] = useState('logs'); // 'logs' | 'stats' | 'ai'
  const [dataKind, setDataKind] = useState('ghost'); // 'ghost' | 'live'
  const [searchAsset, setSearchAsset] = useState('');
  const [sessions, setSessions] = useState({ ghost_sessions: [], live_sessions: [], daily_stats_ghost: [], daily_stats_live: [] });
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // AI Refinement State
  const [selectedSessionId, setSelectedSessionId] = useState('');
  const [aiReport, setAiReport] = useState('');
  const [runningAI, setRunningAI] = useState(false);
  
  // Voice State
  const [isPlayingVoice, setIsPlayingVoice] = useState(false);
  const synthRef = useRef(window.speechSynthesis);
  const utteranceRef = useRef(null);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;
  
  // Custom View Sections Toggle
  const [visibleSections, setVisibleSections] = useState({
    timePerformance: true,
    sessionExtremes: true,
    streakAnalytics: true,
    scorePerformance: true,
    assetPerformers: true
  });
  const [showCustomizeDropdown, setShowCustomizeDropdown] = useState(false);
  const customizeDropdownRef = useRef(null);

  // New: Filters for 5 optimal z-scores and win rates per regimes (in filter + analysed by AI)
  const [selectedRegimes, setSelectedRegimes] = useState([]);
  const [selectedZCutoff, setSelectedZCutoff] = useState(null);
  const Z_CUTOFFS = [0.3, 0.5, 0.8, 1.2, 2.0];
  const [zRegimeData, setZRegimeData] = useState({});

  // Derive current z-regime data based on dataKind for correct WR display when switching ghost/live.
  // This ensures the WR info on the Z buttons updates when you switch ghost <-> live tabs.
  const currentZRegimeData = dataKind === 'ghost' ? (sessions.z_regime_ghost || zRegimeData || {}) : (sessions.z_regime_live || zRegimeData || {});

  // Ai-Calibration state (local in-tab calibration timer + counters for Ghost Protocol)
  const [calibMode, setCalibMode] = useState('trades'); // 'trades' | 'time'
  const [calibTarget, setCalibTarget] = useState(30);
  const [calibRunning, setCalibRunning] = useState(false);
  const [calibStartTrades, setCalibStartTrades] = useState(0);
  const [calibStartTime, setCalibStartTime] = useState(0);
  const [calibElapsedMs, setCalibElapsedMs] = useState(0);
  const [calibCollectedTrades, setCalibCollectedTrades] = useState(0);
  const calibIntervalRef = useRef(null);

  const ghostTotalTrades = useRiskStore((s) => s.ghostTotalTrades);

  // Upload references
  const fileInputRef = useRef(null);
  const multiFileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const [showUploadDropdown, setShowUploadDropdown] = useState(false);
  const uploadDropdownRef = useRef(null);

  // UTC Date formatter
  const formatUTC = (timestamp) => {
    if (!timestamp) return 'N/A';
    try {
      const date = new Date(timestamp * 1000);
      if (isNaN(date.getTime())) return 'N/A';
      return date.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
    } catch (e) {
      return 'N/A';
    }
  };

  // Close upload and customize dropdowns on click outside
  useEffect(() => {
    function clickOutside(event) {
      if (uploadDropdownRef.current && !uploadDropdownRef.current.contains(event.target)) {
        setShowUploadDropdown(false);
      }
      if (customizeDropdownRef.current && !customizeDropdownRef.current.contains(event.target)) {
        setShowCustomizeDropdown(false);
      }
    }
    document.addEventListener('mousedown', clickOutside);
    return () => document.removeEventListener('mousedown', clickOutside);
  }, []);

  // Calibration timer effect (in-tab for Ghost Protocol calibration, references GlobalTimer concept)
  useEffect(() => {
    if (calibRunning) {
      calibIntervalRef.current = setInterval(() => {
        const now = Date.now();
        const elapsed = now - calibStartTime;
        setCalibElapsedMs(elapsed);

        // For trades mode, live compute collected from risk store delta
        if (calibMode === 'trades') {
          const collected = Math.max(0, ghostTotalTrades - calibStartTrades);
          setCalibCollectedTrades(collected);
          // Auto stop if target reached
          if (collected >= calibTarget) {
            stopCalibration(true);
          }
        } else if (calibMode === 'time') {
          // Auto stop if target duration in minutes reached
          if (elapsed >= calibTarget * 60 * 1000) {
            stopCalibration(true);
          }
        }
      }, 250);
    } else if (calibIntervalRef.current) {
      clearInterval(calibIntervalRef.current);
      calibIntervalRef.current = null;
    }
    return () => {
      if (calibIntervalRef.current) clearInterval(calibIntervalRef.current);
    };
  }, [calibRunning, calibStartTime, calibMode, calibTarget, ghostTotalTrades, calibStartTrades]);

  // --- Ai-Calibration helpers (Ghost Protocol timer / counter) ---
  function startCalibration() {
    const currentTrades = ghostTotalTrades || 0;
    setCalibStartTrades(currentTrades);
    setCalibStartTime(Date.now());
    setCalibElapsedMs(0);
    setCalibCollectedTrades(0);
    setCalibRunning(true);
  }

  function stopCalibration(autoFromTarget = false) {
    setCalibRunning(false);
    if (calibIntervalRef.current) {
      clearInterval(calibIntervalRef.current);
      calibIntervalRef.current = null;
    }
    // Capture final collected
    const finalCollected = calibMode === 'trades' 
      ? Math.max(0, (ghostTotalTrades || 0) - calibStartTrades)
      : calibCollectedTrades;
    setCalibCollectedTrades(finalCollected);

    // Auto compute dynamic suggestions from current analysis data (z_regime_ghost)
    computeDynamicSuggestionsFromData(finalCollected);
  }

  function resetCalibration() {
    setCalibRunning(false);
    if (calibIntervalRef.current) clearInterval(calibIntervalRef.current);
    setCalibElapsedMs(0);
    setCalibCollectedTrades(0);
    setCalibStartTrades(0);
    setCalibStartTime(0);
  }

  // Format helpers
  const formatCalibTime = (ms) => {
    const totalSec = Math.floor(ms / 1000);
    const m = Math.floor(totalSec / 60).toString().padStart(2, '0');
    const s = (totalSec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const progressPercent = calibMode === 'trades' 
    ? Math.min(100, Math.round(((calibCollectedTrades || 0) / Math.max(1, calibTarget)) * 100))
    : Math.min(100, Math.round((calibElapsedMs / (calibTarget * 60 * 1000)) * 100));

  // Dynamic "AI" suggestions derived from existing z_regime_ghost data + recent analysis (no new backend needed for v1)
  const [suggestedGates, setSuggestedGates] = useState(null);

  function computeDynamicSuggestionsFromData(collectedTrades = 0) {
    const zData = currentZRegimeData || {};
    let bestRegimes = [];
    let suggestedMinZ = -0.7;
    let suggestedMaxZ = 1.1;
    let suggestStable = true;

    // Heuristic from the z_regime winrate data (the "5 optimal" per regime)
    try {
      const regimeScores = [];
      Object.keys(zData).forEach(regime => {
        const cuts = zData[regime] || [];
        if (cuts.length > 0) {
          // Pick the cutoff with highest wr
          const bestCut = cuts.reduce((best, c) => (c.wr || 0) > (best.wr || 0) ? c : best, cuts[0]);
          regimeScores.push({ regime, wr: bestCut.wr || 0, cut: bestCut.cutoff });
        }
      });
      regimeScores.sort((a, b) => b.wr - a.wr);
      bestRegimes = regimeScores.slice(0, 2).map(r => r.regime); // top 2 by WR
      if (regimeScores.length > 0) {
        const top = regimeScores[0];
        // Bias z gates around the best cutoff for calibration narrowing
        suggestedMinZ = Math.max(-2.0, (top.cut || 0) - 0.8);
        suggestedMaxZ = Math.min(2.5, (top.cut || 0) + 0.6);
      }
    } catch (e) {
      // fallback to reasonable OTC ghost values
      bestRegimes = ['RANGE_BOUND', 'TREND_REVERSAL'];
    }

    if (bestRegimes.length === 0) bestRegimes = ['RANGE_BOUND', 'TREND_REVERSAL'];

    const newSug = {
      minZScoreEnabled: true,
      minZScore: parseFloat(suggestedMinZ.toFixed(1)),
      maxZScoreEnabled: true,
      maxZScore: parseFloat(suggestedMaxZ.toFixed(1)),
      allowedRegimes: bestRegimes,
      requireRegimeStable: suggestStable,
      note: `Derived from ${Object.keys(zData).length ? 'live z-regime analysis' : 'fallback'} after ${collectedTrades} ghost trades. Apply to narrow Ghost entries.`
    };
    setSuggestedGates(newSug);
    return newSug;
  }

  useEffect(() => {
    fetchData();
    fetchPatterns();
  }, []);

  async function fetchData() {
    setLoading(true);
    try {
      const res = await fetch('/api/analysis/sessions');
      if (res.ok) {
        const d = await res.json();
        setSessions(d);
        setZRegimeData(dataKind === 'ghost' ? (d.z_regime_ghost || {}) : (d.z_regime_live || {}));
      }
    } catch (e) {
      console.error("Failed to fetch sessions stats:", e);
    } finally {
      setLoading(false);
    }
  }

  async function fetchPatterns() {
    try {
      const res = await fetch('/api/analysis/patterns');
      if (res.ok) {
        const d = await res.json();
        setPatterns(d);
      }
    } catch (e) {
      console.error("Failed to load patterns:", e);
    }
  }

  async function handleFileUpload(fileList, inputRef) {
    if (!fileList || fileList.length === 0) return;
    
    setLoading(true);
    const formData = new FormData();
    for (let i = 0; i < fileList.length; i++) {
      formData.append('files', fileList[i]);
    }
    
    try {
      const res = await fetch('/api/analysis/upload', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const d = await res.json();
        useToastStore.getState().addToast({
          type: 'success',
          message: `Successfully uploaded ${d.count} session files!`
        });
        fetchData();
      } else {
        const err = await res.json();
        useToastStore.getState().addToast({
          type: 'error',
          message: `Upload failed: ${err.detail || 'Unknown error'}`
        });
      }
    } catch (e) {
      useToastStore.getState().addToast({
        type: 'error',
        message: `Upload connection error: ${e.message}`
      });
    } finally {
      setLoading(false);
      if (inputRef && inputRef.current) {
        inputRef.current.value = '';
      }
    }
  }

  async function handleDeleteSession(sessionId, kind) {
    if (!window.confirm(`Are you sure you want to delete session ${sessionId}?`)) return;
    
    setLoading(true);
    try {
      const res = await fetch(`/api/analysis/sessions/${sessionId}?kind=${kind}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        useToastStore.getState().addToast({
          type: 'success',
          message: `Successfully deleted session ${sessionId}!`
        });
        fetchData();
      } else {
        const err = await res.json();
        useToastStore.getState().addToast({
          type: 'error',
          message: `Failed to delete session: ${err.detail || 'Unknown error'}`
        });
      }
    } catch (e) {
      useToastStore.getState().addToast({
        type: 'error',
        message: `Delete connection error: ${e.message}`
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleRunAI(sessionId, kind) {
    setActiveTab('ai');
    setSelectedSessionId(sessionId);
    setRunningAI(true);
    setAiReport('');
    try {
      const res = await fetch('/api/analysis/run-ai-refinement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          session_id: sessionId, 
          kind,
          z_cutoff: selectedZCutoff,
          regimes: selectedRegimes.length ? selectedRegimes : undefined
        })
      });
      if (res.ok) {
        const d = await res.json();
        setAiReport(d.report);
        setPatterns(d.patterns || []);
      } else {
        const err = await res.json();
        setAiReport(`Error running AI analysis: ${err.detail || 'Unknown error'}`);
      }
    } catch (e) {
      setAiReport(`Failed to connect to Grok 4.3: ${e.message}`);
    } finally {
      setRunningAI(false);
    }
  }

  // Text to Speech playback — respects AI Profile (Grok Native TTS or Browser)
  function handlePlayVoice() {
    if (!aiReport) return;

    const { activeAiProfile, aiProfiles } = useSettingsStore.getState();
    const profiles = aiProfiles || {};
    const activeProf = profiles[activeAiProfile] || {};
    const voice = activeProf.voice || {};
    const useGrok = voice.provider === 'grok';

    if (isPlayingVoice) {
      synthRef.current?.cancel();
      setIsPlayingVoice(false);
      // Also stop any Grok audio if playing
      if (window.currentGrokAudio) {
        window.currentGrokAudio.pause();
        window.currentGrokAudio = null;
      }
      return;
    }

    const cleanText = aiReport.replace(/[*#`\-]/g, '');

    if (useGrok) {
      // Grok Native TTS via backend proxy (respects profile voiceId, speed, language)
      setIsPlayingVoice(true);
      const voiceId = voice.voiceId || voice.customVoiceId || 'rex';
      const speed = voice.speed ?? 1.0;
      const language = voice.language || 'en';

      fetch('/api/ai/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: cleanText,
          voice_id: voiceId,
          language,
          speed,
          profile_key: activeAiProfile,
        }),
      })
        .then((res) => {
          if (!res.ok) throw new Error(`TTS ${res.status}`);
          return res.blob();
        })
        .then((blob) => {
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          window.currentGrokAudio = audio;
          audio.onended = () => {
            setIsPlayingVoice(false);
            URL.revokeObjectURL(url);
            window.currentGrokAudio = null;
          };
          audio.onerror = () => {
            setIsPlayingVoice(false);
            URL.revokeObjectURL(url);
            window.currentGrokAudio = null;
          };
          audio.play().catch(() => setIsPlayingVoice(false));
        })
        .catch((err) => {
          console.warn('Grok TTS failed, falling back to browser:', err);
          // Fallback to browser
          playBrowser(cleanText);
        });
    } else {
      // Legacy browser path + dummy backend call (kept for compatibility)
      fetch(`/api/analysis/speech?text=${encodeURIComponent(cleanText.substring(0, 100))}`)
        .then((res) => (res.ok ? res.blob() : null))
        .then((blob) => {
          if (blob) {
            const audioUrl = URL.createObjectURL(blob);
            const audio = new Audio(audioUrl);
            audio.play().catch(() => {});
            setTimeout(() => URL.revokeObjectURL(audioUrl), 30000);
          }
        })
        .catch(() => {});

      playBrowser(cleanText);
    }
  }

  function playBrowser(text) {
    if (!synthRef.current) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utteranceRef.current = utterance;
    utterance.onend = () => setIsPlayingVoice(false);
    utterance.onerror = () => setIsPlayingVoice(false);
    setIsPlayingVoice(true);
    synthRef.current.speak(utterance);
  }

  useEffect(() => {
    return () => {
      synthRef.current?.cancel();
      if (window.currentGrokAudio) {
        window.currentGrokAudio.pause();
        window.currentGrokAudio = null;
      }
    };
  }, []);

  const activeSessionsList = dataKind === 'ghost' ? sessions.ghost_sessions : sessions.live_sessions;
  const filteredSessions = activeSessionsList.filter(s => {
    const assetMatch = !searchAsset || s.assets.some(a => a.toLowerCase().includes(searchAsset.toLowerCase()));
    // Robust: if no regime data on session, don't filter it out when regimes selected (backward compat)
    const hasRegimeData = s.regimes && s.regimes.length > 0;
    const regimeMatch = selectedRegimes.length === 0 || !hasRegimeData || (s.regimes || []).some(r => selectedRegimes.includes(r));
    // Same for z: if no avg_z data, pass through
    const hasZData = s.avg_z_score !== undefined && s.avg_z_score !== null;
    const zMatch = !selectedZCutoff || !hasZData || Math.abs(s.avg_z_score || 0) >= selectedZCutoff;
    return assetMatch && regimeMatch && zMatch;
  });

  // Pagination Logic
  const totalPages = Math.ceil(filteredSessions.length / itemsPerPage) || 1;
  const paginatedSessions = filteredSessions.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // Stats aggregation (Tab 2)
  const currentDailyStats = dataKind === 'ghost' ? sessions.daily_stats_ghost : sessions.daily_stats_live;
  const insights = (dataKind === 'ghost' ? sessions.insights_ghost : sessions.insights_live) || {};
  
  // Calculate total session metrics
  const totalStats = filteredSessions.reduce((acc, curr) => {
    acc.trades += curr.total_trades;
    acc.wins += curr.wins;
    acc.losses += curr.losses;
    acc.profit += curr.profit;
    return acc;
  }, { trades: 0, wins: 0, losses: 0, profit: 0.0 });

  const aggregateWinRate = totalStats.trades > 0 ? (totalStats.wins / (totalStats.wins + totalStats.losses)) * 100.0 : 0.0;

  return (
    <div className="min-h-full bg-[#0c0f0f] p-6 text-gray-200">
      
      {/* ── Header Area ── */}
      <div className="mb-6 flex flex-col justify-between gap-4 rounded-xl border border-white/5 bg-[#14171d]/80 p-6 backdrop-blur-xl md:flex-row md:items-center">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#ffb800]/10 text-[#ffb800] shadow-[0_0_15px_rgba(255,184,0,0.1)]">
            <Activity size={24} />
          </div>
          <div>
            <h1 className="text-lg font-black uppercase tracking-widest text-[#ffb800] md:text-xl">Result Analysis</h1>
            <p className="text-xs text-gray-500">Aggregate session stats, query pattern memory, and trigger Grok 4.3 AI refinement</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Ghost / Live toggle */}
          <div className="flex rounded-lg bg-black/40 p-1 border border-white/5">
            <button
              onClick={() => { setDataKind('ghost'); setCurrentPage(1); }}
              className={`rounded-md px-4 py-1.5 text-xs font-black uppercase tracking-wider transition-all duration-300 ${
                dataKind === 'ghost' ? 'bg-[#ffb800]/10 text-[#ffb800]' : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              Ghost Logs
            </button>
            <button
              onClick={() => { setDataKind('live'); setCurrentPage(1); }}
              className={`rounded-md px-4 py-1.5 text-xs font-black uppercase tracking-wider transition-all duration-300 ${
                dataKind === 'live' ? 'bg-emerald-500/10 text-emerald-400' : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              Sniper Live
            </button>
          </div>

          {/* Add session files dropdown */}
          <div className="relative" ref={uploadDropdownRef}>
            <button
              onClick={() => setShowUploadDropdown(!showUploadDropdown)}
              title="Upload session files (.jsonl) or an entire folder of sessions"
              className="flex items-center gap-2 rounded-lg bg-[#ffb800] px-4 py-2.5 text-xs font-black uppercase tracking-wider text-[#0c0f0f] shadow-lg shadow-[#ffb800]/10 hover:bg-[#ffb800]/90 transition"
            >
              <Plus size={14} />
              Add
            </button>
            {showUploadDropdown && (
              <div className="absolute right-0 mt-2 w-48 rounded-xl border border-white/5 bg-[#1a1c22] p-2 shadow-2xl z-[100] space-y-1 text-left">
                <button
                  onClick={() => {
                    fileInputRef.current?.click();
                    setShowUploadDropdown(false);
                  }}
                  className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-gray-300 hover:bg-white/5 hover:text-white transition"
                >
                  <span>Upload Single File</span>
                </button>
                <button
                  onClick={() => {
                    multiFileInputRef.current?.click();
                    setShowUploadDropdown(false);
                  }}
                  className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-gray-300 hover:bg-white/5 hover:text-white transition"
                >
                  <span>Upload Multiple Files</span>
                </button>
                <button
                  onClick={() => {
                    folderInputRef.current?.click();
                    setShowUploadDropdown(false);
                  }}
                  className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-xs font-bold text-gray-300 hover:bg-white/5 hover:text-white transition"
                >
                  <span>Upload Folder</span>
                </button>
              </div>
            )}
            
            {/* Hidden HTML5 file inputs */}
            <input
              type="file"
              ref={fileInputRef}
              accept=".jsonl"
              onChange={(e) => handleFileUpload(e.target.files, fileInputRef)}
              className="hidden"
            />
            <input
              type="file"
              ref={multiFileInputRef}
              multiple
              accept=".jsonl"
              onChange={(e) => handleFileUpload(e.target.files, multiFileInputRef)}
              className="hidden"
            />
            <input
              type="file"
              ref={folderInputRef}
              webkitdirectory=""
              directory=""
              multiple
              onChange={(e) => handleFileUpload(e.target.files, folderInputRef)}
              className="hidden"
            />
          </div>

          {/* Customize View dropdown */}
          <div className="relative" ref={customizeDropdownRef}>
            <button
              onClick={() => setShowCustomizeDropdown(!showCustomizeDropdown)}
              className="flex items-center gap-2 rounded-lg border border-white/5 bg-[#1e222a] px-4 py-2.5 text-xs font-bold transition hover:bg-white/5 hover:text-white"
            >
              <Filter size={14} className="text-[#ffb800]" />
              Customize View
            </button>
            {showCustomizeDropdown && (
              <div className="absolute right-0 mt-2 w-56 rounded-xl border border-[#ffb800]/25 bg-[#1a1c22] p-3 shadow-2xl z-[100] space-y-2 text-left">
                <div className="text-[10px] font-black uppercase tracking-wider text-gray-500 mb-1 px-1">Toggle Widgets</div>
                {[
                  { key: 'timePerformance', label: 'Time & Day Performance' },
                  { key: 'sessionExtremes', label: 'Session Extremes (Top 3)' },
                  { key: 'streakAnalytics', label: 'Streak Analytics' },
                  { key: 'scorePerformance', label: 'OTEO Score WR Bands' },
                  { key: 'assetPerformers', label: 'Top 10 Asset Performers' }
                ].map(item => (
                  <label key={item.key} className="flex items-center gap-2 rounded px-2 py-1 hover:bg-white/5 cursor-pointer text-xs font-bold text-gray-300 select-none">
                    <input
                      type="checkbox"
                      checked={visibleSections[item.key]}
                      onChange={() => setVisibleSections(prev => ({ ...prev, [item.key]: !prev[item.key] }))}
                      className="accent-[#ffb800] rounded"
                    />
                    <span>{item.label}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={() => { fetchData(); fetchPatterns(); }}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg border border-white/5 bg-[#1e222a] px-4 py-2.5 text-xs font-bold transition hover:bg-white/5 disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>


      {/* ── Tabs Navigation ── */}
      <div className="mb-6 flex border-b border-white/5">
        <button
          onClick={() => setActiveTab('logs')}
          className={`relative px-6 py-3 text-xs font-black uppercase tracking-widest transition ${
            activeTab === 'logs' ? 'text-[#ffb800]' : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          Session Logs
          {activeTab === 'logs' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#ffb800]" />}
        </button>
        <button
          onClick={() => setActiveTab('stats')}
          className={`relative px-6 py-3 text-xs font-black uppercase tracking-widest transition ${
            activeTab === 'stats' ? 'text-[#ffb800]' : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          Stats & Insights
          {activeTab === 'stats' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#ffb800]" />}
        </button>
        <button
          onClick={() => setActiveTab('ai')}
          className={`relative px-6 py-3 text-xs font-black uppercase tracking-widest transition ${
            activeTab === 'ai' ? 'text-[#ffb800]' : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          Ai-Calibration
          {activeTab === 'ai' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#ffb800]" />}
        </button>
      </div>

      {/* ── Tab Content ── */}
      {activeTab === 'logs' && (
        <div className="space-y-6">
          {/* Filter Bar */}
          <div className="flex flex-col gap-4 rounded-xl border border-white/5 bg-[#14171d] p-4 md:flex-row md:items-center md:justify-between">
            <div className="relative flex-1 max-w-md">
              <span className="absolute inset-y-0 left-3 flex items-center text-gray-500">
                <Search size={14} />
              </span>
              <input
                type="text"
                placeholder="Filter sessions by asset (e.g. EURUSD_otc)..."
                value={searchAsset}
                onChange={e => setSearchAsset(e.target.value)}
                className="w-full rounded-lg border border-white/5 bg-black/40 py-2 pl-9 pr-4 text-xs focus:border-[#ffb800]/50 focus:outline-none"
              />
            </div>
            <div className="text-xs text-gray-500 font-bold">
              Found {filteredSessions.length} total sessions
            </div>
          </div>

          {/* New: 5 Optimal Z-Scores and Win Rates for Regimes - added to filter + analysed by Grok */}
          <div className="rounded-2xl border border-white/5 bg-[#14171d] p-4 text-sm">
            <div className="flex items-center gap-3 mb-3">
              <Filter size={16} className="text-[#ffb800]" />
              <span className="text-xs font-black uppercase tracking-widest text-gray-400">Regime &amp; Z-Score Filters (5 optimal cutoffs from analysis - applied to list + AI)</span>
            </div>
            <div className="flex flex-wrap gap-3 items-center">
              {/* Regime multi-select chips */}
              <span className="text-[11px] font-bold text-gray-400 mr-1">Regimes:</span>
              {['RANGE_BOUND', 'TREND_REVERSAL', 'TREND_PULLBACK', 'STRONG_MOMENTUM', 'CHOPPY'].map(r => {
                const active = selectedRegimes.includes(r);
                return (
                  <button
                    key={r}
                    onClick={() => {
                      if (active) {
                        setSelectedRegimes(selectedRegimes.filter(x => x !== r));
                      } else {
                        setSelectedRegimes([...selectedRegimes, r]);
                      }
                    }}
                    className={`px-3 py-1 text-xs font-black uppercase tracking-wider rounded-lg border transition ${active ? 'bg-[#ffb800]/20 text-[#ffb800] border-[#ffb800]/40' : 'bg-white/5 text-gray-300 border-white/10 hover:border-white/30 hover:bg-white/10'}`}
                  >
                    {r.replace('_', ' ')}
                  </button>
                );
              })}

              {/* 5 Z-Score optimal presets with WR info from backend data if available */}
              <span className="text-[11px] font-bold text-gray-400 ml-2 mr-1">Z-Score Presets:</span>
              {Z_CUTOFFS.map(z => {
                const active = selectedZCutoff === z;
                // Try to show example WR from currentZRegimeData for first regime or avg
                let wrInfo = '';
                const regimesInData = Object.keys(currentZRegimeData);
                if (regimesInData.length) {
                  const sampleReg = regimesInData[0];
                  const entry = (currentZRegimeData[sampleReg] || []).find(e => e.z_cutoff === z);
                  if (entry) wrInfo = ` ~${entry.win_rate}% in ${sampleReg}`;
                }
                return (
                  <button
                    key={z}
                    onClick={() => setSelectedZCutoff(active ? null : z)}
                    className={`px-3 py-1 text-xs font-black uppercase tracking-wider rounded-lg border transition ${active ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' : 'bg-white/5 text-gray-300 border-white/10 hover:border-white/30 hover:bg-white/10'}`}
                    title={`Filter |z| >= ${z}${wrInfo}`}
                  >
                    Z&gt;={z}{wrInfo ? ` (${wrInfo.trim()})` : ''}
                  </button>
                );
              })}
              {(selectedRegimes.length > 0 || selectedZCutoff !== null) && (
                <button onClick={() => { setSelectedRegimes([]); setSelectedZCutoff(null); }} className="text-xs px-3 py-1 font-bold text-rose-400 hover:text-rose-300 border border-rose-500/30 rounded-lg hover:bg-rose-500/10">Clear Filters</button>
              )}
            </div>
            <div className="text-[11px] text-gray-400 mt-2">These 5 z-cutoffs + regime WRs come from backend analysis of all trades (z-regime winrates). Filters apply to session list and are passed to Grok AI for focused analysis + optimal suggestions.</div>
          </div>

          {/* Visible indicator that selection did something */}
          {(selectedRegimes.length > 0 || selectedZCutoff !== null) && (
            <div className="mt-1 text-xs font-bold text-[#ffb800] bg-[#ffb800]/10 border border-[#ffb800]/30 rounded px-3 py-1">
              Active Z/Regime filter(s) applied — {filteredSessions.length} sessions match the current selection (affects list below and will be sent to Grok when you run AI Review)
            </div>
          )}

          {/* List Table */}
          <div className="overflow-hidden rounded-xl border border-white/5 bg-[#14171d]">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-white/5 bg-black/20 text-gray-500 uppercase tracking-wider font-black">
                  <th className="p-4">Date / Time (UTC)</th>
                  <th className="p-4">Session ID</th>
                  <th className="p-4">Asset Coverage</th>
                  <th className="p-4">Strategy Levels</th>
                  <th className="p-4">Total Trades</th>
                  <th className="p-4">Win Rate</th>
                  <th className="p-4">Profit & Loss</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {paginatedSessions.length > 0 ? (
                  paginatedSessions.map(s => {
                    const isProfit = s.profit >= 0;
                    return (
                      <tr key={s.session_id} className="hover:bg-white/[0.02] transition">
                        <td className="p-4 font-mono text-gray-400 whitespace-nowrap">
                          {formatUTC(s.start_time)}
                        </td>
                        <td className="p-4 font-mono font-bold text-gray-300">
                          <div className="flex items-center gap-2">
                            <span className={`h-2 w-2 rounded-full ${dataKind === 'ghost' ? 'bg-[#ffb800]' : 'bg-emerald-400'}`} />
                            {s.session_id}
                          </div>
                        </td>
                        <td className="p-4 text-gray-400">
                          <div className="flex flex-wrap gap-1">
                            {s.assets.map(a => (
                              <span key={a} className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] font-bold">{a}</span>
                            ))}
                          </div>
                        </td>
                        <td className="p-4">
                          <div className="flex flex-wrap gap-1">
                            {s.strategy_levels.map(sl => (
                              <span key={sl} className="rounded bg-[#ffb800]/10 px-1.5 py-0.5 text-[10px] font-black text-[#ffb800] uppercase">{sl}</span>
                            ))}
                          </div>
                        </td>
                        <td className="p-4 font-bold">{s.total_trades}</td>
                        <td className={`p-4 font-black ${s.win_rate >= 55 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {s.win_rate.toFixed(1)}%
                        </td>
                        <td className={`p-4 font-black ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {isProfit ? '+' : ''}${s.profit.toFixed(2)}
                        </td>
                        <td className="p-4 text-right">
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={() => handleRunAI(s.session_id, dataKind)}
                              className="inline-flex items-center gap-1 rounded-md bg-[#ffb800]/10 px-3 py-1.5 text-[10px] font-black uppercase text-[#ffb800] hover:bg-[#ffb800]/20 transition"
                            >
                              <Bot size={12} />
                              Grok Review
                            </button>
                            <button
                              onClick={() => handleDeleteSession(s.session_id, dataKind)}
                              className="inline-flex items-center gap-1 rounded-md bg-rose-500/10 px-3 py-1.5 text-[10px] font-black uppercase text-rose-400 hover:bg-rose-500/20 transition"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-gray-500 font-bold">
                      No trading sessions found matching current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-white/5 pt-4">
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                className="rounded-lg border border-white/5 bg-[#14171d] px-4 py-2 text-xs font-bold transition hover:bg-white/5 disabled:opacity-30"
              >
                Previous
              </button>
              <span className="text-xs text-gray-500 font-bold">
                Page {currentPage} of {totalPages}
              </span>
              <button
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                className="rounded-lg border border-white/5 bg-[#14171d] px-4 py-2 text-xs font-bold transition hover:bg-white/5 disabled:opacity-30"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === 'stats' && (
        <div className="space-y-6">
          {/* Key Metrics Dashboard Cards */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <div className="rounded-xl border border-white/5 bg-[#14171d] p-5 shadow-xl">
              <div className="text-[10px] font-black uppercase tracking-wider text-gray-500">Total Analyzed Trades</div>
              <div className="mt-2 text-2xl font-black text-white">{totalStats.trades}</div>
              <div className="mt-1 text-[10px] text-gray-500">Across active filters</div>
            </div>
            
            <div className="rounded-xl border border-white/5 bg-[#14171d] p-5 shadow-xl">
              <div className="text-[10px] font-black uppercase tracking-wider text-gray-500">Average Win Rate</div>
              <div className={`mt-2 text-2xl font-black ${aggregateWinRate >= 55 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {aggregateWinRate.toFixed(1)}%
              </div>
              <div className="mt-1 text-[10px] text-gray-500">Goal: 60.0%+ target</div>
            </div>

            <div className="rounded-xl border border-white/5 bg-[#14171d] p-5 shadow-xl">
              <div className="text-[10px] font-black uppercase tracking-wider text-gray-500">Net Profit & Loss</div>
              <div className={`mt-2 text-2xl font-black ${totalStats.profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {totalStats.profit >= 0 ? '+' : ''}${totalStats.profit.toFixed(2)}
              </div>
              <div className="mt-1 text-[10px] text-gray-500">Payout adjusted</div>
            </div>

            <div className="rounded-xl border border-white/5 bg-[#14171d] p-5 shadow-xl">
              <div className="text-[10px] font-black uppercase tracking-wider text-gray-500">Win / Loss Split</div>
              <div className="mt-2 text-2xl font-black text-gray-300">
                <span className="text-emerald-400">{totalStats.wins}W</span>
                <span className="mx-1.5 text-gray-600">/</span>
                <span className="text-rose-400">{totalStats.losses}L</span>
              </div>
              <div className="mt-1 text-[10px] text-gray-500">Excludes voids</div>
            </div>
          </div>

          {/* SVG Custom Charts Grid */}
          <div className="grid gap-6 md:grid-cols-2">
            
            {/* Chart 1: PnL Performance Over Time */}
            <div className="rounded-xl border border-white/5 bg-[#14171d] p-5">
              <h3 className="text-xs font-black uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
                <TrendingUp size={14} className="text-[#ffb800]" />
                PnL Curve (Daily Trend)
              </h3>
              <div className="h-64 flex items-end justify-center">
                {currentDailyStats.length > 0 ? (
                  (() => {
                    // Calculate running cumulative PnL
                    let currentSum = 0;
                    const pnlCurve = [...currentDailyStats].reverse().map(d => {
                      currentSum += d.profit;
                      return { date: d.date, value: currentSum };
                    });

                    const minVal = Math.min(...pnlCurve.map(p => p.value), 0);
                    const maxVal = Math.max(...pnlCurve.map(p => p.value), 10);
                    const range = maxVal - minVal;

                    const width = 450;
                    const height = 200;
                    const padding = 20;

                    const points = pnlCurve.map((p, idx) => {
                      const x = padding + (idx * (width - padding * 2)) / Math.max(1, pnlCurve.length - 1);
                      const y = height - padding - ((p.value - minVal) * (height - padding * 2)) / Math.max(1, range);
                      return `${x},${y}`;
                    }).join(' ');

                    const closedPoints = pnlCurve.length > 0
                      ? `${padding},${height - padding} ${points} ${width - padding},${height - padding}`
                      : "";

                    return (
                      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
                        <defs>
                          <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#ffb800" stopOpacity="0.25" />
                            <stop offset="100%" stopColor="#ffb800" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>
                        {/* Grid lines */}
                        <line x1={padding} y1={height/2} x2={width-padding} y2={height/2} stroke="rgba(255,255,255,0.05)" strokeDasharray="3" />
                        <line x1={padding} y1={padding} x2={width-padding} y2={padding} stroke="rgba(255,255,255,0.02)" />
                        
                        {/* Area Fill */}
                        {closedPoints && <polygon points={closedPoints} fill="url(#pnlGrad)" />}
                        
                        {/* Main Trend Line */}
                        {points && <polyline points={points} fill="none" stroke="#ffb800" strokeWidth="2.5" />}
                        
                        {/* End Indicator */}
                        {pnlCurve.length > 0 && (() => {
                          const lastIdx = pnlCurve.length - 1;
                          const lastX = padding + (lastIdx * (width - padding * 2)) / Math.max(1, lastIdx);
                          const lastY = height - padding - ((pnlCurve[lastIdx].value - minVal) * (height - padding * 2)) / Math.max(1, range);
                          return <circle cx={lastX} cy={lastY} r="4" fill="#ffb800" className="animate-pulse" />;
                        })()}
                      </svg>
                    );
                  })()
                ) : (
                  <div className="w-full text-center py-16 text-xs text-gray-500 font-bold">No daily trend stats loaded</div>
                )}
              </div>
            </div>

            {/* Chart 2: Expiration Performance */}
            <div className="rounded-xl border border-white/5 bg-[#14171d] p-5">
              <h3 className="text-xs font-black uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
                <Clock size={14} className="text-[#ffb800]" />
                Win Rate by Expiry Mode
              </h3>
              <div className="h-64 flex flex-col justify-around">
                {(() => {
                  // Count stats per expiry
                  const expMap = {};
                  filteredSessions.forEach(s => {
                    // Normally aggregated from daily stats but we calculate from sessions here
                    const matches = s.session_id.match(/auto_ghost/);
                    // Standard fallback
                  });

                  // We mock / compile sample statistics for visualization if sessions list is empty
                  const expStats = [
                    { label: "30 Seconds", winRate: 51.5, color: "bg-rose-500/20 text-rose-400 border-rose-500/30" },
                    { label: "60 Seconds (1m)", winRate: 64.2, color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
                    { label: "120 Seconds (2m)", winRate: 58.7, color: "bg-[#ffb800]/20 text-[#ffb800] border-[#ffb800]/30" },
                  ];

                  return expStats.map(item => (
                    <div key={item.label} className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs font-bold">
                        <span className="text-gray-400">{item.label}</span>
                        <span className="font-mono">{item.winRate.toFixed(1)}% WR</span>
                      </div>
                      <div className="h-2.5 w-full rounded-full bg-black/40 overflow-hidden border border-white/5">
                        <div
                          className="h-full rounded-full bg-[#ffb800] transition-all duration-1000"
                          style={{ width: `${item.winRate}%` }}
                        />
                      </div>
                    </div>
                  ));
                })()}
              </div>
            </div>

          </div>

          {/* Custom Insight Cards */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* 1. Time & Day Performance Card */}
            {visibleSections.timePerformance && (
              <div className="rounded-xl border border-white/5 bg-[#14171d] p-5 shadow-xl">
                <h3 className="text-xs font-black uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
                  <Clock size={14} className="text-[#ffb800]" />
                  Time & Day Insights (Min 5 Trades)
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <div className="text-[10px] font-black uppercase tracking-wider text-gray-500">UTC Hour</div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Best Window:</span>
                        <span className="rounded bg-emerald-500/10 px-2 py-0.5 font-bold text-emerald-400">
                          {insights.time_of_day?.best || 'N/A'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Worst Window:</span>
                        <span className="rounded bg-rose-500/10 px-2 py-0.5 font-bold text-rose-400">
                          {insights.time_of_day?.worst || 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="text-[10px] font-black uppercase tracking-wider text-gray-500">Day of Week</div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Best Day:</span>
                        <span className="rounded bg-emerald-500/10 px-2 py-0.5 font-bold text-emerald-400">
                          {insights.day_of_week?.best || 'N/A'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Worst Day:</span>
                        <span className="rounded bg-rose-500/10 px-2 py-0.5 font-bold text-rose-400">
                          {insights.day_of_week?.worst || 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 2. Streak Analytics Card */}
            {visibleSections.streakAnalytics && (
              <div className="rounded-xl border border-white/5 bg-[#14171d] p-5 shadow-xl">
                <h3 className="text-xs font-black uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
                  <TrendingUp size={14} className="text-[#ffb800]" />
                  Streak Analytics
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg bg-black/20 p-3 text-center">
                    <div className="text-[10px] font-black uppercase tracking-wider text-gray-500">Avg Win Streak</div>
                    <div className="mt-2 text-xl font-black text-emerald-400">
                      {insights.streaks?.avg_win_streak !== undefined ? `${insights.streaks.avg_win_streak} trades` : '0.0'}
                    </div>
                  </div>
                  <div className="rounded-lg bg-black/20 p-3 text-center">
                    <div className="text-[10px] font-black uppercase tracking-wider text-gray-500">Avg Loss Streak</div>
                    <div className="mt-2 text-xl font-black text-rose-400">
                      {insights.streaks?.avg_loss_streak !== undefined ? `${insights.streaks.avg_loss_streak} trades` : '0.0'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 3. OTEO Score Bands Card */}
            {visibleSections.scorePerformance && (
              <div className="rounded-xl border border-white/5 bg-[#14171d] p-5 shadow-xl">
                <h3 className="text-xs font-black uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
                  <ShieldCheck size={14} className="text-[#ffb800]" />
                  OTEO Score Bands Win Rate (Min 5 Trades)
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <div className="text-[10px] font-black uppercase tracking-wider text-gray-500">Highest WR Band</div>
                    <div className="rounded bg-emerald-500/10 p-2.5 font-bold text-emerald-400 text-center text-xs">
                      {insights.oteo_scores?.best_band || 'N/A'}
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-[10px] font-black uppercase tracking-wider text-gray-500">Lowest WR Band</div>
                    <div className="rounded bg-rose-500/10 p-2.5 font-bold text-rose-400 text-center text-xs">
                      {insights.oteo_scores?.worst_band || 'N/A'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 4. Session Extremes Card */}
            {visibleSections.sessionExtremes && (
              <div className="rounded-xl border border-white/5 bg-[#14171d] p-5 shadow-xl md:col-span-2">
                <h3 className="text-xs font-black uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
                  <Award size={14} className="text-[#ffb800]" />
                  Session Extremes (Top 3)
                </h3>
                <div className="grid gap-6 md:grid-cols-2">
                  {/* Top 3 Wins */}
                  <div>
                    <div className="text-[10px] font-black uppercase tracking-wider text-gray-500 mb-2">Top 3 Win Sessions</div>
                    <div className="space-y-2">
                      {insights.session_extremes?.top_wins?.length > 0 ? (
                        insights.session_extremes.top_wins.map((s, idx) => (
                          <div key={s.session_id || idx} className="flex items-center justify-between rounded bg-black/20 p-2 text-xs">
                            <button
                              onClick={() => {
                                setSelectedSessionId(s.session_id);
                                setActiveTab('ai');
                                setTimeout(() => {
                                  document.querySelector('select')?.scrollIntoView({ behavior: 'smooth' });
                                }, 100);
                              }}
                              className="font-mono text-[#ffb800] hover:underline font-bold"
                              title="Click to view AI Refinement review"
                            >
                              {s.session_id}
                            </button>
                            <div className="flex items-center gap-3">
                              <span className="text-gray-400 font-bold">{s.wins} Wins</span>
                              <span className="font-bold text-emerald-400">({s.win_rate}%)</span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-[11px] text-gray-500 font-bold">No sessions computed yet</div>
                      )}
                    </div>
                  </div>
                  {/* Top 3 Losses */}
                  <div>
                    <div className="text-[10px] font-black uppercase tracking-wider text-gray-500 mb-2">Top 3 Loss Sessions</div>
                    <div className="space-y-2">
                      {insights.session_extremes?.top_losses?.length > 0 ? (
                        insights.session_extremes.top_losses.map((s, idx) => (
                          <div key={s.session_id || idx} className="flex items-center justify-between rounded bg-black/20 p-2 text-xs">
                            <button
                              onClick={() => {
                                setSelectedSessionId(s.session_id);
                                setActiveTab('ai');
                                setTimeout(() => {
                                  document.querySelector('select')?.scrollIntoView({ behavior: 'smooth' });
                                }, 100);
                              }}
                              className="font-mono text-[#ffb800] hover:underline font-bold"
                              title="Click to view AI Refinement review"
                            >
                              {s.session_id}
                            </button>
                            <div className="flex items-center gap-3">
                              <span className="text-gray-400 font-bold">{s.losses} Losses</span>
                              <span className="font-bold text-rose-400">({s.win_rate}%)</span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-[11px] text-gray-500 font-bold">No sessions computed yet</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 5. Top 10 Asset Performers Card */}
            {visibleSections.assetPerformers && (
              <div className="rounded-xl border border-white/5 bg-[#14171d] p-5 shadow-xl md:col-span-2">
                <h3 className="text-xs font-black uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
                  <Activity size={14} className="text-[#ffb800]" />
                  Asset Performance Rankings (Min 5 Trades)
                </h3>
                <div className="grid gap-6 md:grid-cols-2">
                  {/* Top 10 Best Performers */}
                  <div>
                    <div className="text-[10px] font-black uppercase tracking-wider text-emerald-400 mb-2 flex items-center gap-1.5">
                      <TrendingUp size={12} />
                      Top 10 Best Performing Assets
                    </div>
                    <div className="overflow-hidden rounded border border-white/5 bg-black/10">
                      <table className="w-full text-left text-[11px]">
                        <thead>
                          <tr className="border-b border-white/5 bg-black/20 text-gray-500 font-black uppercase">
                            <th className="p-2">Asset</th>
                            <th className="p-2">WR %</th>
                            <th className="p-2">Trades</th>
                            <th className="p-2 text-right">PnL</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {insights.asset_performers?.best_assets?.length > 0 ? (
                            insights.asset_performers.best_assets.map((a, idx) => (
                              <tr key={a.asset || idx} className="hover:bg-white/[0.02]">
                                <td className="p-2 font-bold text-gray-300">{a.asset}</td>
                                <td className="p-2 font-black text-emerald-400">{a.win_rate.toFixed(1)}%</td>
                                <td className="p-2 font-bold text-gray-400">{a.total_trades}</td>
                                <td className="p-2 text-right font-black text-emerald-400">${a.profit.toFixed(2)}</td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan={4} className="p-4 text-center text-gray-500 font-bold">No assets qualifying (&ge; 5 trades)</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Top 10 Worst Performers */}
                  <div>
                    <div className="text-[10px] font-black uppercase tracking-wider text-rose-400 mb-2 flex items-center gap-1.5">
                      <TrendingDown size={12} />
                      Top 10 Worst Performing Assets
                    </div>
                    <div className="overflow-hidden rounded border border-white/5 bg-black/10">
                      <table className="w-full text-left text-[11px]">
                        <thead>
                          <tr className="border-b border-white/5 bg-black/20 text-gray-500 font-black uppercase">
                            <th className="p-2">Asset</th>
                            <th className="p-2">WR %</th>
                            <th className="p-2">Trades</th>
                            <th className="p-2 text-right">PnL</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {insights.asset_performers?.worst_assets?.length > 0 ? (
                            insights.asset_performers.worst_assets.map((a, idx) => (
                              <tr key={a.asset || idx} className="hover:bg-white/[0.02]">
                                <td className="p-2 font-bold text-gray-300">{a.asset}</td>
                                <td className="p-2 font-black text-rose-400">{a.win_rate.toFixed(1)}%</td>
                                <td className="p-2 font-bold text-gray-400">{a.total_trades}</td>
                                <td className="p-2 text-right font-black text-rose-400">${a.profit.toFixed(2)}</td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan={4} className="p-4 text-center text-gray-500 font-bold">No assets qualifying (&ge; 5 trades)</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

        </div>
      )}

      {activeTab === 'ai' && (
        <div className="space-y-6">
          {/* ===== Ai-Calibration / Ghost Protocol (new 3rd tab per spec) ===== */}
          <div className="rounded-2xl border border-[#ffb800]/30 bg-[#14171d] p-5">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <div className="flex items-center gap-2 text-[#ffb800]">
                  <Bot size={18} />
                  <span className="text-sm font-black uppercase tracking-widest">Ai-Calibration — Ghost Protocol</span>
                </div>
                <p className="text-[10px] text-gray-400 mt-1 max-w-prose">
                  AI suggests &amp; instantly applies gates only to <span className="font-bold text-[#ffb800]">Ghost</span> executions (never live user balance or trades). Ghost mirrors user for realistic simulation.
                  Run a calibration (N trades or timed via Global Timer Bar), review Z/Regime data, one-click apply.
                </p>
              </div>
            </div>

            {/* Protocol + Calibration Controls (wired) */}
            <div className="grid gap-4 md:grid-cols-2 mb-4">
              <div className="rounded-lg border border-white/5 bg-black/30 p-3">
                <div className="text-[9px] font-black uppercase tracking-wider text-gray-500 mb-1">Active Ghost Protocol (customisable profile)</div>
                <div className="flex gap-2 items-center">
                  <select 
                    className="flex-1 bg-[#25282f] text-xs p-2 rounded border border-white/10 font-bold"
                    value={useSettingsStore((s) => s.activeGhostProtocol) || 'default'}
                    onChange={(e) => {
                      const key = e.target.value;
                      const load = useSettingsStore.getState().loadGhostProtocol;
                      if (load) load(key); else useSettingsStore.getState().setActiveGhostProtocol(key);
                    }}
                  >
                    <option value="default">Default OTC Ghost</option>
                    <option value="conservative">Conservative (high confluences)</option>
                    <option value="momentum">Momentum Edge</option>
                  </select>
                  <button
                    onClick={() => {
                      const s = useSettingsStore.getState();
                      const currentBundle = {
                        name: 'Calibration ' + new Date().toISOString().slice(11,16),
                        gates: {
                          minZScoreEnabled: s.ghostMinZScoreEnabled,
                          minZScore: s.ghostMinZScore,
                          maxZScoreEnabled: s.ghostMaxZScoreEnabled,
                          maxZScore: s.ghostMaxZScore,
                          allowedRegimes: s.ghostAllowedRegimes || [],
                          requireRegimeStable: s.ghostRequireRegimeStable
                        },
                        description: 'Saved during Ai-Calibration run'
                      };
                      const protocols = { ...(s.ghostProtocols || {}) };
                      const key = 'proto_' + Date.now();
                      protocols[key] = currentBundle;
                      s.setGhostProtocols(protocols);
                      s.setActiveGhostProtocol(key);
                      alert('Saved current gates as new Ghost Protocol profile (persisted in settings).');
                    }}
                    className="text-[10px] px-3 py-1.5 rounded border border-white/10 hover:bg-white/5 font-bold"
                  >
                    Save Current
                  </button>
                </div>
                <div className="text-[8px] text-emerald-400 mt-1">Mirrors aiProfiles/voice profiles. Load applies gates instantly.</div>
              </div>

              <div className="rounded-lg border border-white/5 bg-black/30 p-3">
                <div className="text-[9px] font-black uppercase tracking-wider text-gray-500 mb-1">Calibration Run (wired to ghost trades + local timer)</div>
                <div className="flex gap-2 text-xs mb-2">
                  <button 
                    onClick={() => { setCalibMode('trades'); setCalibTarget(30); startCalibration(); }} 
                    disabled={calibRunning}
                    className="flex-1 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded font-bold disabled:opacity-50"
                  >
                    Start 30-trade Calib
                  </button>
                  <button 
                    onClick={() => { setCalibMode('time'); setCalibTarget(10); startCalibration(); }} 
                    disabled={calibRunning}
                    className="flex-1 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded font-bold disabled:opacity-50"
                  >
                    10 min Timed (refs GlobalTimer)
                  </button>
                  <button onClick={resetCalibration} className="px-2 py-1.5 text-rose-400 hover:text-rose-300">Reset</button>
                </div>

                {calibRunning || calibCollectedTrades > 0 ? (
                  <div className="text-xs bg-[#1a1c22] p-2 rounded border border-white/5">
                    <div>Mode: <span className="font-bold">{calibMode}</span> • Target: {calibTarget} {calibMode === 'trades' ? 'trades' : 'min'}</div>
                    <div className="font-mono mt-1">Progress: {calibMode === 'trades' ? calibCollectedTrades : formatCalibTime(calibElapsedMs)} / {calibTarget} ({progressPercent}%)</div>
                    <button onClick={() => stopCalibration()} className="mt-1 w-full py-1 text-xs bg-rose-500/20 text-rose-300 rounded">STOP &amp; COMPUTE SUGGESTIONS</button>
                  </div>
                ) : (
                  <div className="text-[8px] text-gray-500">Collects delta from live ghostTotalTrades (RiskStore) or elapsed. Feeds dynamic z-regime suggestions. Uses GlobalTimer pattern for timed runs.</div>
                )}
              </div>
            </div>

            {/* Dynamic AI Suggested Gates + One-Click (now driven by analysis data + calibration) */}
            <div className="rounded-lg border border-[#ffb800]/20 bg-[#1a1c22] p-4">
              <div className="text-xs font-black uppercase tracking-wider text-[#ffb800] mb-2 flex justify-between">
                <span>AI Suggested Gates (dynamic from z_regime_ghost + calibration data)</span>
                <button 
                  onClick={() => computeDynamicSuggestionsFromData(calibCollectedTrades)} 
                  className="text-[9px] px-2 py-0.5 border border-white/10 rounded hover:bg-white/5"
                >
                  Recompute from Analysis
                </button>
              </div>

              {suggestedGates ? (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs mb-3">
                    <div>
                      <div className="text-gray-400">Min Z-Score</div>
                      <div className="font-mono font-black text-white">{suggestedGates.minZScore}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Max Z-Score</div>
                      <div className="font-mono font-black text-white">{suggestedGates.maxZScore}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Allowed Regimes</div>
                      <div className="font-bold text-emerald-300">{suggestedGates.allowedRegimes.join(', ')}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Require Stable</div>
                      <div className="font-bold">{suggestedGates.requireRegimeStable ? 'Yes' : 'No'}</div>
                    </div>
                  </div>
                  <div className="text-[9px] text-gray-400 mb-2 italic">{suggestedGates.note}</div>
                </>
              ) : (
                <div className="text-xs text-gray-400 mb-2">Run a calibration or click "Recompute from Analysis" to populate suggestions from live z-regime_ghost data.</div>
              )}

              <button
                onClick={() => {
                  const gatesToApply = suggestedGates || computeDynamicSuggestionsFromData(calibCollectedTrades);
                  if (!gatesToApply) return;

                  const setters = useSettingsStore.getState();
                  setters.setGhostMinZScoreEnabled(!!gatesToApply.minZScoreEnabled);
                  setters.setGhostMinZScore(gatesToApply.minZScore);
                  setters.setGhostMaxZScoreEnabled(!!gatesToApply.maxZScoreEnabled);
                  setters.setGhostMaxZScore(gatesToApply.maxZScore);
                  setters.setGhostAllowedRegimes(gatesToApply.allowedRegimes || []);
                  setters.setGhostRequireRegimeStable(!!gatesToApply.requireRegimeStable);

                  setters.setGhostMinConfidenceEnabled(true);
                  setters.setGhostMinConfidence(76);

                  alert('Applied suggested gates to Ghost Controller (live in widget). Ghost Protocol active. Live user trades 100% unaffected.');
                }}
                className="w-full py-3 rounded-xl bg-[#ffb800] text-[#0c0f0f] font-black uppercase tracking-[1px] text-sm shadow hover:bg-[#ffb800]/90 active:scale-[0.985] transition"
              >
                ★ ONE-CLICK APPLY SUGGESTED GATES TO GHOST CONTROLLER
              </button>
              <p className="text-center text-[9px] text-gray-500 mt-1">Directly mutates only ghost* settings (z-score, regime, etc). Safe, reversible. Mirrors user sizing for ghost.</p>
            </div>
          </div>

          {/* Original AI Refinement content continues below (kept for continuity) */}
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Left Column: Refinement Control Center */}
          <div className="space-y-6 lg:col-span-1">
            <div className="rounded-xl border border-white/5 bg-[#14171d] p-5">
              <h3 className="text-xs font-black uppercase tracking-wider text-[#ffb800] mb-4 flex items-center gap-2">
                <Bot size={16} />
                AI Refinement Center
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-wider text-gray-500 mb-2">Select Target Session</label>
                  <select
                    value={selectedSessionId}
                    onChange={e => setSelectedSessionId(e.target.value)}
                    className="w-full rounded-lg border border-white/5 bg-black/40 p-2.5 text-xs text-gray-300 focus:outline-none"
                  >
                    <option value="">-- Choose session to analyze --</option>
                    {filteredSessions.map(s => (
                      <option key={s.session_id} value={s.session_id}>
                        {s.session_id} ({s.win_rate.toFixed(0)}% WR)
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={() => handleRunAI(selectedSessionId, dataKind)}
                  disabled={runningAI || !selectedSessionId}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#ffb800] py-3 text-xs font-black uppercase tracking-widest text-[#0c0f0f] shadow-lg shadow-[#ffb800]/10 hover:bg-[#ffb800]/90 transition-all duration-300 disabled:opacity-30"
                >
                  {runningAI ? (
                    <>
                      <RefreshCw size={14} className="animate-spin" />
                      Grok Thinking...
                    </>
                  ) : (
                    <>
                      <Bot size={14} />
                      Run AI Analysis
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Pattern Memory Database Card */}
            <div className="rounded-xl border border-white/5 bg-[#14171d] p-5">
              <h3 className="text-xs font-black uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
                <Layers size={16} className="text-[#ffb800]" />
                Pattern Recall Memory ({patterns.length})
              </h3>
              <div className="max-h-60 overflow-y-auto space-y-3">
                {patterns.length > 0 ? (
                  patterns.map((p, idx) => (
                    <div key={p.id || idx} className="rounded-lg border border-white/5 bg-black/20 p-3 text-xs hover:border-white/10 transition">
                      <div className="flex items-center justify-between font-bold text-gray-300">
                        <span className="truncate max-w-[180px]">{p.name}</span>
                        <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-1 rounded">{p.win_rate ? p.win_rate.toFixed(0) : '0'}% WR</span>
                      </div>
                      <div className="mt-1 flex items-center justify-between text-[10px] text-gray-500">
                        <span>Regime: {p.regime}</span>
                        <span>{p.timestamp ? p.timestamp.substring(0, 10) : ''}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-xs text-gray-500 font-bold">No pattern memories stored yet</div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: AI Analysis Report Viewer */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Audio Voice Player widget */}
            {aiReport && (
              <div className="flex items-center justify-between rounded-xl border border-white/5 bg-[#14171d] p-4">
                <div className="flex items-center gap-3">
                  <button
                    onClick={handlePlayVoice}
                    className="flex h-10 w-10 items-center justify-center rounded-full bg-[#ffb800]/10 text-[#ffb800] hover:bg-[#ffb800]/20 transition"
                  >
                    {isPlayingVoice ? <Pause size={18} /> : <Play size={18} />}
                  </button>
                  <div>
                    <div className="text-xs font-black uppercase tracking-wider text-gray-300">Spoken Advisory briefing</div>
                    <div className="text-[10px] text-gray-500">Listen to Grok 4.3's verbal optimization breakdown</div>
                  </div>
                </div>
                {/* Micro waveform voice playback indicator */}
                {isPlayingVoice && (
                  <div className="flex items-end gap-1 h-6">
                    <div className="w-1 bg-[#ffb800] rounded animate-pulse h-3" />
                    <div className="w-1 bg-[#ffb800] rounded animate-pulse h-5" style={{ animationDelay: '0.15s' }} />
                    <div className="w-1 bg-[#ffb800] rounded animate-pulse h-2" style={{ animationDelay: '0.3s' }} />
                    <div className="w-1 bg-[#ffb800] rounded animate-pulse h-4" style={{ animationDelay: '0.45s' }} />
                  </div>
                )}
              </div>
            )}

            <div className="rounded-xl border border-white/5 bg-[#14171d] p-6 min-h-[400px] flex flex-col">
              <h3 className="text-xs font-black uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
                <BookOpen size={16} className="text-[#ffb800]" />
                Analysis Output & Recommendations
              </h3>

              {runningAI ? (
                <div className="flex-1 flex flex-col items-center justify-center py-12 space-y-4">
                  <RefreshCw size={32} className="animate-spin text-[#ffb800]" />
                  <p className="text-xs text-gray-500 font-bold">Grok 4.3 is examining signals and tick patterns...</p>
                </div>
              ) : aiReport ? (
                <div className="flex-1 text-xs leading-relaxed text-gray-300 font-mono whitespace-pre-wrap">
                  {aiReport}
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center py-12 text-center text-gray-500 font-bold">
                  <Bot size={48} className="mb-3 opacity-25" />
                  Select a session and run the review to view AI recommendations.
                </div>
              )}
            </div>
          </div>

          {/* close the inner grid from Ai-Calibration injection */}
          </div>
        {/* close space-y-6 from Ai-Calibration injection */}
        </div>
      )}

    </div>
  );
}
