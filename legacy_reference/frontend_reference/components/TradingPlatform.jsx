import React, { useState, useEffect, useRef, useCallback } from 'react';
import useWebSocket from 'react-use-websocket';
import axios from 'axios';
import { io } from 'socket.io-client';
import Sparkline from './Sparkline';
import TopBar from './TopBar';
import GhostStatsPanel from './GhostStatsPanel';
import MultiChartView from './MultiChartView';
import SettingsView from './SettingsView';
import AccountManagementView from './AccountManagementView';
import { useOpsControl } from '../hooks/useOpsControl';  // FIX ISSUE-7: Use shared hook
import { normalizeAsset, formatAssetLabel } from '../utils/assetUtils';
import { API_URL, WS_URL, STREAM_URL } from '../config';
import {
  Terminal,
  Activity,
  TrendingUp,
  TrendingDown,
  Clock,
  RefreshCw,
  Search,
  Star,
  Zap,
  AlertTriangle,
} from 'lucide-react';

const TradingPlatform = ({ initialDemoConnected, initialRealConnected, onLogout }) => {
  // Account State
  const [activeAccount, setActiveAccount] = useState(initialDemoConnected ? 'demo' : 'real');
  const [demoConnected, setDemoConnected] = useState(initialDemoConnected);
  const [realConnected, setRealConnected] = useState(initialRealConnected);
  const [balances, setBalances] = useState({ demo: 0, real: 0 });
  const [statuses, setStatuses] = useState({ demo: 'disconnected', real: 'disconnected' });

  // Trading State
  const [assets, setAssets] = useState([]);
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [tradeAmount, setTradeAmount] = useState(10.0);
  const [expiration, setExpiration] = useState(60);
  const [tradeHistory, setTradeHistory] = useState([]);

  // Asset Panel State
  const [searchQuery, setSearchQuery] = useState('');
  const [quickAssets, setQuickAssets] = useState([]);
  const [refreshInterval, setRefreshInterval] = useState(0);

  // View State (Trading vs MultiChart vs Settings vs Account)
  const [currentView, setCurrentView] = useState('trading');

  // UI State
  const [loading, setLoading] = useState(false);
  const [tradingBusy, setTradingBusy] = useState({ call: false, put: false });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Trading State Extras
  const [activeTrades, setActiveTrades] = useState([]);

  // Streaming State
  const [streamPrices, setStreamPrices] = useState([]);
  const [oteoScore, setOteoScore] = useState(0);
  const [oteoAction, setOteoAction] = useState('CALL');
  const [streamStatus, setStreamStatus] = useState('disconnected');
  const [manipulation, setManipulation] = useState({});
  const [oteoWarmup, setOteoWarmup] = useState({ ready: false, ticks: 0, asset: null });

  // FIX ISSUE-7: Use shared ops control hook — removes ~90 lines of duplicated code
  const {
    chromeStatus, collectorStatus, opsBusy, isBackendReachable,
    fetchOpsStatus,
    handleStartChrome, handleStopChrome,
    handleStartStream, handleStopStream,
  } = useOpsControl(STREAM_URL);

  // FIX-4 (NEW-BUG-B): Local SSID busy state — setOpsBusy from useOpsControl
  // only tracks chrome/stream; it does not expose a setter for ssid.
  const [ssidBusy, setSsidBusy] = useState(false);

  // Refs
  const refreshTimerRef = useRef(null);
  const socketRef = useRef(null);
  // FIX ISSUE-10: Use a ref for selectedAsset in the warmup_status handler
  // to avoid stale closure. The handler is set up once (empty deps), so it
  // would capture selectedAsset at mount time (null). Using a ref ensures
  // we always read the current value.
  const selectedAssetRef = useRef(selectedAsset);
  useEffect(() => { selectedAssetRef.current = selectedAsset; }, [selectedAsset]);

  // WebSocket
  const { lastMessage } = useWebSocket(WS_URL, {
    shouldReconnect: () => true,
    reconnectAttempts: 10,
    reconnectInterval: 3000,
  });

  /**
   * FIX-4 (NEW-BUG-B): Start SSID connection.
   * Uses local setSsidBusy — setOpsBusy from useOpsControl has no ssid key.
   */
  const handleStartSsid = useCallback(async () => {
    const isDemo = activeAccount === 'demo';
    setSsidBusy(true);
    try {
      const response = await axios.post(`${API_URL}/connect`, { demo: isDemo });
      if (response.data.success) {
        if (isDemo) {
          setDemoConnected(true);
          setBalances(prev => ({ ...prev, demo: response.data.balance || 0 }));
          setStatuses(prev => ({ ...prev, demo: 'connected' }));
        } else {
          setRealConnected(true);
          setBalances(prev => ({ ...prev, real: response.data.balance || 0 }));
          setStatuses(prev => ({ ...prev, real: 'connected' }));
        }
        setSuccess(`Connected to ${activeAccount} account`);
      } else {
        setError(response.data.message || 'Failed to connect');
      }
    } catch (err) {
      setError(err.response?.data?.message || err.response?.data?.detail || 'Failed to connect');
    } finally {
      setSsidBusy(false);
      setTimeout(() => { setSuccess(''); setError(''); }, 3000);
    }
  }, [activeAccount]);

  /**
   * FIX-4 (NEW-BUG-B): Stop SSID connection.
   * Uses local setSsidBusy — setOpsBusy from useOpsControl has no ssid key.
   */
  const handleStopSsid = useCallback(async () => {
    const isDemo = activeAccount === 'demo';
    setSsidBusy(true);
    if (isDemo) {
      setDemoConnected(false);
      setStatuses(prev => ({ ...prev, demo: 'disconnected' }));
    } else {
      setRealConnected(false);
      setStatuses(prev => ({ ...prev, real: 'disconnected' }));
    }
    setSuccess(`Disconnected from ${activeAccount} account`);
    setSsidBusy(false);
    setTimeout(() => { setSuccess(''); }, 3000);
  }, [activeAccount]);

  // ─────────────────────────────────────────────────────────────────────────────
  // WEBSOCKET & SOCKET.IO SETUP
  // ─────────────────────────────────────────────────────────────────────────────

  // Handle WS Messages (WebSocket for account updates)
  useEffect(() => {
    if (!lastMessage) return;
    try {
      const data = JSON.parse(lastMessage.data);
      if (data.type === 'update') {
        if (data.active_trades) {
          setActiveTrades(data.active_trades);
        }
        if (data.accounts) {
          if (data.accounts.demo) {
            setBalances(prev => ({ ...prev, demo: data.accounts.demo.balance || 0 }));
            setStatuses(prev => ({ ...prev, demo: data.accounts.demo.status }));
            if (activeAccount === 'demo' && data.accounts.demo.history) {
              setTradeHistory(data.accounts.demo.history);
            }
          }
          if (data.accounts.real) {
            setBalances(prev => ({ ...prev, real: data.accounts.real.balance || 0 }));
            setStatuses(prev => ({ ...prev, real: data.accounts.real.status }));
            if (activeAccount === 'real' && data.accounts.real.history) {
              setTradeHistory(data.accounts.real.history);
            }
          }
        }
      }
    } catch (e) {
      console.error('WS Parse Error', e);
      setError('Live data parsing error');
      setTimeout(() => setError(''), 3000);
    }
  }, [lastMessage, activeAccount]);

  // Socket.IO setup (for market data streaming)
  useEffect(() => {
    fetchAssets();
    const stored = localStorage.getItem('quickAssets');
    if (stored) setQuickAssets(JSON.parse(stored));

    socketRef.current = io(STREAM_URL);
    socketRef.current.on('connect', () => setStreamStatus('connected'));
    socketRef.current.on('disconnect', () => setStreamStatus('disconnected'));
    socketRef.current.on('market_data', (data) => {
      if (data.price) setStreamPrices(prev => [...prev.slice(-100), data.price]);
      if (data.oteo_score !== undefined) setOteoScore(data.oteo_score);
      const dir = data.recommended || data.action;
      if (dir) setOteoAction(dir);
      if (data.manipulation) setManipulation(data.manipulation);
    });

    socketRef.current.on('warmup_status', (data) => {
      // FIX ISSUE-10: Use selectedAssetRef.current to avoid stale closure.
      const incomingAsset = normalizeAsset(data.asset);
      const currentAsset  = normalizeAsset(selectedAssetRef.current?.id);
      if (incomingAsset && incomingAsset === currentAsset) {
        setOteoWarmup({
          ready: data.ready,
          ticks: data.ticks_received,
          asset: data.asset,
        });
      }
    });

    return () => {
      if (socketRef.current) socketRef.current.disconnect();
    };
  }, []);

  useEffect(() => {
    if (socketRef.current && selectedAsset && streamStatus === 'connected') {
      // Normalize asset ID to canonical format (EURUSDOTC) before emitting.
      // Backend rooms use this format: market_data:EURUSDOTC
      socketRef.current.emit('focus_asset', { asset: normalizeAsset(selectedAsset.id) });
      setStreamPrices([]);
    }
  }, [selectedAsset, streamStatus]);

  useEffect(() => {
    if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    if (refreshInterval > 0) {
      refreshTimerRef.current = setInterval(refreshAssets, refreshInterval * 60 * 1000);
    }
    return () => clearInterval(refreshTimerRef.current);
  }, [refreshInterval]);

  // ─────────────────────────────────────────────────────────────────────────────
  // API CALLS
  // ─────────────────────────────────────────────────────────────────────────────

  const fetchAssets = async () => {
    try {
      const response = await axios.get(`${API_URL}/assets`, { params: { demo: activeAccount === 'demo' } });
      setAssets(response.data);
      if (response.data.length > 0 && !selectedAsset) setSelectedAsset(response.data[0]);
    } catch (err) {
      console.error('Failed to fetch assets', err);
      setError(err.response?.data?.detail || err.message || 'Failed to fetch assets');
      setTimeout(() => setError(''), 3000);
    }
  };

  const refreshAssets = async () => {
    setLoading(true);
    try {
      await axios.post(`${API_URL}/assets/refresh`, null, { params: { demo: activeAccount === 'demo' } });
      await fetchAssets();
      setSuccess('Assets refreshed');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail || err.message || 'Failed to refresh assets';
      // 400 = not connected yet — not an error worth showing
      if (status !== 400) {
        setError(detail);
        setTimeout(() => setError(''), 3000);
      }
    } finally {
      setLoading(false);
    }
  };

  const executeTrade = async (direction) => {
    if (!selectedAsset) return;
    setTradingBusy(prev => ({ ...prev, [direction]: true }));
    setError('');
    try {
      const response = await axios.post(`${API_URL}/trade`, {
        asset_id: selectedAsset.id,
        direction,
        amount: parseFloat(tradeAmount),
        expiration: parseInt(expiration),
        demo: activeAccount === 'demo'
      });
      if (response.data.success) {
        setSuccess(`${direction.toUpperCase()} — ${selectedAsset.name}`);
        // Add trade to local history immediately as PENDING
        setTradeHistory(prev => [{
          asset: selectedAsset.name || selectedAsset.id,
          direction: direction,
          amount: parseFloat(tradeAmount),
          status: 'PENDING',
          trade_id: response.data.trade_id || null,
          open_time: Date.now() / 1000
        }, ...prev]);
      } else {
        setError(response.data.message || response.data.detail || 'Trade failed');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setTradingBusy(prev => ({ ...prev, [direction]: false }));
      setTimeout(() => { setError(''); setSuccess(''); }, 3000);
    }
  };

  const toggleQuickAsset = (assetId) => {
    const newQuick = quickAssets.includes(assetId)
      ? quickAssets.filter(id => id !== assetId)
      : [...quickAssets, assetId];
    setQuickAssets(newQuick);
    localStorage.setItem('quickAssets', JSON.stringify(newQuick));
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER HELPERS
  // ─────────────────────────────────────────────────────────────────────────────

  const filteredAssets = assets.filter(a =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.id.toLowerCase().includes(searchQuery.toLowerCase())
  );
  const quickAssetList = assets.filter(a => quickAssets.includes(a.id));
  const accountStatus = statuses[activeAccount] || 'disconnected';

  const payoutColor = (payout) => {
    if (payout >= 90) return 'text-neon bg-neon/10 shadow-glow-neon';
    if (payout >= 80) return 'text-cyan bg-cyan/10';
    return 'text-amber bg-amber/10';
  };

  const effectiveStreamStatus = streamStatus === 'connected' && collectorStatus === 'streaming'
    ? 'streaming'
    : streamStatus === 'connected'
    ? 'connected'
    : 'disconnected';

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen bg-abyss text-white font-mono overflow-hidden">
      <GhostStatsPanel />

      {/* ══ LEFT SIDEBAR — ASSETS ══════════════════════════════════ */}
      <div className="w-72 flex flex-col border-r border-white/5"
           style={{ background: 'rgba(10,15,30,0.9)', backdropFilter: 'blur(16px)' }}>

        {/* Sidebar header */}
        <div className="p-4 space-y-3 border-b border-white/5">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search assets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full glass-card rounded-lg pl-9 pr-4 py-2 text-xs text-white placeholder-slate-600
                         focus:outline-none focus:border-cyan/40 focus:shadow-glow-cyan transition-all"
            />
          </div>

          {/* Refresh row */}
          <div className="flex items-center justify-between">
            <button
              onClick={refreshAssets}
              disabled={loading}
              className="btn-shimmer relative flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold
                         bg-cyan/10 text-cyan border border-cyan/20 hover:border-cyan/50 hover:shadow-glow-cyan
                         transition-all overflow-hidden disabled:opacity-40"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              REFRESH
            </button>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              className="glass-card rounded-md text-xs px-2 py-1.5 focus:outline-none text-slate-300"
            >
              <option value="0">Manual</option>
              <option value="1">1 min</option>
              <option value="3">3 min</option>
              <option value="5">5 min</option>
              <option value="10">10 min</option>
            </select>
          </div>
        </div>

        {/* Quick Select */}
        {quickAssets.length > 0 && (
          <div className="flex-none border-b border-white/5">
            <div className="px-4 pt-3 pb-1 flex items-center gap-1.5 text-[10px] font-bold text-amber/70 uppercase tracking-widest">
              <Zap className="w-3 h-3" /> Quick Select
            </div>
            {quickAssetList.map(asset => (
              <div key={asset.id} onClick={() => setSelectedAsset(asset)}
                   className={`px-4 py-2 cursor-pointer flex justify-between items-center transition-all
                               hover:bg-white/3 group
                               ${selectedAsset?.id === asset.id
                                 ? 'border-l-2 border-neon bg-neon/5 shadow-[inset_0_0_20px_rgba(0,255,157,0.03)]'
                                 : 'border-l-2 border-transparent'}`}>
                <span className={`text-xs font-bold ${selectedAsset?.id === asset.id ? 'text-neon text-glow-neon' : 'text-white'}`}>
                  {asset.name}
                </span>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${payoutColor(asset.payout)}`}>
                    {asset.payout}%
                  </span>
                  <Star
                    className="w-3 h-3 text-amber fill-amber cursor-pointer hover:scale-125 transition-transform"
                    onClick={(e) => { e.stopPropagation(); toggleQuickAsset(asset.id); }}
                  />
                </div>
              </div>
            ))}
            <div className="gradient-divider my-1" />
          </div>
        )}

        {/* All Assets */}
        {/* Navigation Tabs */}
        <div className="flex-none flex flex-col gap-1 p-4 border-b border-white/5">
          <button 
            onClick={() => setCurrentView('trading')}
            className={`text-left px-3 py-2 rounded-lg text-xs font-bold transition-all ${currentView === 'trading' ? 'bg-cyan/20 text-cyan border border-cyan/30' : 'text-slate-400 hover:bg-white/5'}`}
          >
            Trading Terminal
          </button>
          <button 
            onClick={() => setCurrentView('multichart')}
            className={`text-left px-3 py-2 rounded-lg text-xs font-bold transition-all ${currentView === 'multichart' ? 'bg-cyan/20 text-cyan border border-cyan/30' : 'text-slate-400 hover:bg-white/5'}`}
          >
            Multi-Chart View
          </button>
          <button 
            onClick={() => setCurrentView('settings')}
            className={`text-left px-3 py-2 rounded-lg text-xs font-bold transition-all ${currentView === 'settings' ? 'bg-cyan/20 text-cyan border border-cyan/30' : 'text-slate-400 hover:bg-white/5'}`}
          >
            Settings
          </button>
          <button 
            onClick={() => setCurrentView('account')}
            className={`text-left px-3 py-2 rounded-lg text-xs font-bold transition-all ${currentView === 'account' ? 'bg-cyan/20 text-cyan border border-cyan/30' : 'text-slate-400 hover:bg-white/5'}`}
          >
            Account
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="px-4 py-2 text-[10px] font-bold text-slate-600 uppercase tracking-widest mt-2">
            All Assets <span className="text-slate-700">({filteredAssets.length})</span>
          </div>
          {filteredAssets.map(asset => (
            <div key={asset.id} onClick={() => setSelectedAsset(asset)}
                 className={`px-4 py-2.5 cursor-pointer flex justify-between items-center transition-all
                             hover:bg-white/3 border-b border-white/3
                             ${selectedAsset?.id === asset.id
                               ? 'border-l-2 border-neon bg-neon/5'
                               : 'border-l-2 border-transparent'}`}>
              <div>
                <div className={`text-xs font-bold ${selectedAsset?.id === asset.id ? 'text-neon' : 'text-white'}`}>
                  {asset.name}
                </div>
                <div className="text-[10px] text-slate-600 mt-0.5">{asset.id}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${payoutColor(asset.payout)}`}>
                  {asset.payout}%
                </span>
                <Star
                  className={`w-3.5 h-3.5 cursor-pointer transition-all
                    ${quickAssets.includes(asset.id)
                      ? 'text-amber fill-amber scale-110'
                      : 'text-slate-700 hover:text-amber hover:scale-110'}`}
                  onClick={(e) => { e.stopPropagation(); toggleQuickAsset(asset.id); }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ══ MAIN CONTENT ══════════════════════════════════════════ */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* ── TOP HEADER ─────────────────────────────────────────── */}
        {/* FIX-6 (NEW-BUG-C): Wrap ops handlers to pass setSuccess/setError callbacks.
            Previously passed bare handlers — TopBar called them with no args so
            setSuccess/setError were undefined and no toast feedback was shown. */}
        <TopBar 
          streamStatus={effectiveStreamStatus}
          chromeStatus={chromeStatus}
          ssidStatus={accountStatus}
          onLogout={onLogout}
          onStartChrome={() => handleStartChrome(setSuccess, setError)}
          onStopChrome={() => handleStopChrome(setSuccess, setError)}
          onStartStream={() => handleStartStream(setSuccess, setError)}
          onStopStream={() => handleStopStream(setSuccess, setError)}
          onStartSsid={handleStartSsid}
          onStopSsid={handleStopSsid}
          isBusy={{ ...opsBusy, ssid: ssidBusy }}
        />

        {/* ── ACCOUNT INFO BAR ──────────────────────────────────── */}
        {currentView === 'trading' && (
        <div className="h-12 glass-card border-b border-white/5 flex items-center justify-between px-6 z-10 flex-none">
          <div className="flex items-center gap-6">
            {/* Account toggle */}
            <div className="flex bg-black/30 rounded-lg p-0.5 border border-white/5">
              <button
                onClick={() => demoConnected && setActiveAccount('demo')}
                disabled={!demoConnected}
                className={`px-4 py-1.5 rounded-md text-xs font-black tracking-wider transition-all ${
                  activeAccount === 'demo'
                    ? 'bg-neon/90 text-black shadow-glow-neon'
                    : 'text-slate-500 hover:text-white'
                } ${!demoConnected ? 'opacity-30 cursor-not-allowed' : ''}`}
              >
                DEMO
              </button>
              <button
                onClick={() => realConnected && setActiveAccount('real')}
                disabled={!realConnected}
                className={`px-4 py-1.5 rounded-md text-xs font-black tracking-wider transition-all ${
                  activeAccount === 'real'
                    ? 'bg-cyan/90 text-black shadow-glow-cyan'
                    : 'text-slate-500 hover:text-white'
                } ${!realConnected ? 'opacity-30 cursor-not-allowed' : ''}`}
              >
                REAL
              </button>
            </div>

            {/* Balance */}
            <div className="flex flex-col leading-tight">
              <span className="text-[9px] text-slate-600 uppercase tracking-widest">Balance</span>
              <span className="text-lg font-black balance-num text-neon text-glow-neon">
                ${balances[activeAccount]?.toFixed(2) || '0.00'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-[10px] text-slate-600">v0.1.0</span>
          </div>
        </div>
        )}

        {/* ── TRADING AREA ────────────────────────────────────────── */}
        <div className="flex-1 p-6 overflow-y-auto relative">
          {currentView === 'multichart' && (
            <MultiChartView socket={socketRef.current} allAssets={assets} onFocusAsset={(assetId) => {
              const matched = assets.find(a => normalizeAsset(a.id) === normalizeAsset(assetId));
              if (matched) {
                setSelectedAsset(matched);
                setCurrentView('trading');
              }
            }} />
          )}

          {currentView === 'settings' && <SettingsView />}
          
          {currentView === 'account' && <AccountManagementView />}

          {currentView === 'trading' && (
            <>

          {/* Toast messages */}
          {(error || success) && (
            <div className={`absolute top-4 left-1/2 -translate-x-1/2 z-50 px-6 py-2.5 rounded-lg text-sm font-bold
                             shadow-lg flex items-center gap-2 transition-all
                             ${error ? 'bg-signal/90 text-white shadow-glow-signal' : 'bg-neon/90 text-black shadow-glow-neon'}`}>
              {error ? <AlertTriangle className="w-4 h-4" /> : <Activity className="w-4 h-4" />}
              {error || success}
            </div>
          )}

          <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">

            {/* ── Chart Card ─── */}
            <div className="glass-card rounded-2xl p-5">
              {/* Card header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan" />
                  <h2 className="text-sm font-black tracking-wider text-white">
                    {selectedAsset ? selectedAsset.name : 'SELECT ASSET'}
                  </h2>
                </div>
                {selectedAsset && (
                  <span className={`text-xs font-black px-2 py-0.5 rounded ${payoutColor(selectedAsset.payout)}`}>
                    {selectedAsset.payout}% PAYOUT
                  </span>
                )}
              </div>

              {/* Sparkline */}
              <div className="h-56 rounded-xl overflow-hidden mb-4 border border-white/5">
                <Sparkline
                  prices={streamPrices}
                  oteoScore={oteoScore}
                  action={oteoAction}
                  manipulation={manipulation}
                />
              </div>

              {/* OTEO Warmup Indicator */}
              {selectedAsset && !oteoWarmup.ready && (
                <div className="flex items-center justify-center gap-2 py-2 bg-amber/5 border border-amber/20 rounded-lg mb-3">
                  <div className="w-2 h-2 rounded-full bg-amber animate-pulse" />
                  <span className="text-[10px] font-bold text-amber uppercase tracking-wider">
                    OTEO Warming: {oteoWarmup.ticks}/50 ticks
                  </span>
                </div>
              )}

              {/* OTEO Ready Indicator */}
              {selectedAsset && oteoWarmup.ready && (
                <div className="flex items-center justify-center gap-2 py-2 bg-neon/5 border border-neon/20 rounded-lg mb-3">
                  <div className="w-2 h-2 rounded-full bg-neon shadow-[0_0_8px_rgba(0,255,157,0.6)]" />
                  <span className="text-[10px] font-bold text-neon uppercase tracking-wider">
                    OTEO Ready
                  </span>
                </div>
              )}

              {/* Controls row */}
              <div className="grid grid-cols-2 gap-3">
                {/* Expiration */}
                <div className="glass-card rounded-xl p-3">
                  <label className="text-[9px] text-slate-600 uppercase tracking-widest block mb-1">Expiration</label>
                  <div className="flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-slate-600" />
                    <select
                      value={expiration}
                      onChange={(e) => setExpiration(Number(e.target.value))}
                      className="bg-transparent text-sm font-black w-full focus:outline-none text-white"
                    >
                      <option value="30">30s</option>
                      <option value="60">1m</option>
                      <option value="120">2m</option>
                      <option value="300">5m</option>
                    </select>
                  </div>
                </div>

                {/* Amount */}
                <div className="glass-card rounded-xl p-3">
                  <label className="text-[9px] text-slate-600 uppercase tracking-widest block mb-1">Amount ($)</label>
                  <input
                    type="number"
                    value={tradeAmount}
                    onChange={(e) => setTradeAmount(e.target.value)}
                    min="1"
                    className="bg-transparent text-sm font-black w-full focus:outline-none text-white"
                  />
                </div>
              </div>
            </div>

            {/* ── Trade Buttons ─── */}
            <div className="flex flex-col gap-4 h-full">
              {/* Active Trades Badge */}
              {activeTrades.length > 0 && (
                <div className="flex items-center justify-center gap-2 py-2 bg-amber/10 border border-amber/20 rounded-xl animate-pulse">
                  <Activity className="w-3 h-3 text-amber" />
                  <span className="text-[10px] font-black text-amber uppercase tracking-widest">
                    {activeTrades.length} ACTIVE TRADES
                  </span>
                </div>
              )}

              {/* CALL */}
              <button
                onClick={() => executeTrade('call')}
                disabled={tradingBusy.call || !selectedAsset}
                className="btn-shimmer relative flex-1 rounded-2xl flex flex-col items-center justify-center gap-2
                           overflow-hidden transition-all group
                           disabled:opacity-40 disabled:cursor-not-allowed
                           active:scale-[0.97]"
                style={{
                  background: 'linear-gradient(135deg, #00c47a 0%, #00a86b 100%)',
                  boxShadow: '0 4px 32px rgba(0,196,122,0.2), inset 0 1px 0 rgba(255,255,255,0.15)'
                }}
              >
                <TrendingUp className="w-10 h-10 group-hover:-translate-y-1 transition-transform duration-200" />
                <span className="text-2xl font-black tracking-widest">CALL</span>
                <span className="text-xs font-bold opacity-60 tracking-widest">HIGHER</span>
              </button>

              {/* PUT */}
              <button
                onClick={() => executeTrade('put')}
                disabled={tradingBusy.put || !selectedAsset}
                className="btn-shimmer relative flex-1 rounded-2xl flex flex-col items-center justify-center gap-2
                           overflow-hidden transition-all group
                           disabled:opacity-40 disabled:cursor-not-allowed
                           active:scale-[0.97]"
                style={{
                  background: 'linear-gradient(135deg, #e02d4c 0%, #c01f3a 100%)',
                  boxShadow: '0 4px 32px rgba(224,45,76,0.2), inset 0 1px 0 rgba(255,255,255,0.1)'
                }}
              >
                <TrendingDown className="w-10 h-10 group-hover:translate-y-1 transition-transform duration-200" />
                <span className="text-2xl font-black tracking-widest">PUT</span>
                <span className="text-xs font-bold opacity-60 tracking-widest">LOWER</span>
              </button>
            </div>

          </div>

          {/* ── Trade History ───────────────────────────────────────── */}
          <div className="max-w-4xl mx-auto mt-6">
            <div className="flex items-center gap-2 mb-3">
              <Terminal className="w-4 h-4 text-slate-600" />
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">
                Session History — {activeAccount.toUpperCase()}
              </h3>
            </div>
            <div className="glass-card rounded-2xl overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/5">
                    {['Time', 'Asset', 'Direction', 'Amount', 'Result'].map(h => (
                      <th key={h} className="px-4 py-3 text-[10px] text-slate-600 uppercase tracking-widest font-bold">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {tradeHistory.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-10 text-center">
                        <div className="flex flex-col items-center gap-2 text-slate-700">
                          <Terminal className="w-8 h-8" />
                          <span className="text-xs">No trades this session</span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    tradeHistory.map((trade, i) => (
                      <tr key={i}
                          className="border-b border-white/3 hover:bg-white/2 transition-colors group">
                        <td className="px-4 py-3 font-mono text-slate-500">
                          {new Date(trade.open_time * 1000).toLocaleTimeString()}
                        </td>
                        <td className="px-4 py-3 font-bold text-white">{trade.asset}</td>
                        <td className={`px-4 py-3 font-black ${trade.direction === 'call' ? 'text-neon' : 'text-signal'}`}>
                          {trade.direction?.toUpperCase()}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">${trade.amount}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-black ${
                            trade.status === 'WIN'
                              ? 'bg-neon/10 text-neon shadow-glow-neon'
                              : trade.status === 'LOSS'
                              ? 'bg-signal/10 text-signal shadow-glow-signal'
                              : 'bg-amber/10 text-amber'
                          }`}>
                            {trade.status || 'PENDING'}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default TradingPlatform;
