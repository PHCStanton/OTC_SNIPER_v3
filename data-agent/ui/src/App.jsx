import React, { useState, useEffect, useMemo } from 'react';
import {
  Database,
  Activity,
  ShieldCheck,
  Zap,
  Filter,
  BarChart3,
  RefreshCcw,
  CheckCircle2,
  XCircle,
  Search,
  Plus,
  Radio,
  Wifi,
  WifiOff,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import {
  buildCustomCatalogEntry,
  canSubmitCustomAsset,
  formatPayoutLabel,
  matchesPayoutFilter,
  resolveSelectedAsset,
  DEFAULT_FULL_ASSET_CATALOG,
} from './assetUtils';
import ConnectSSIDModal from './components/ConnectSSIDModal';

export default function App() {
  const [telemetry, setTelemetry] = useState(null);
  const [rawTicks, setRawTicks] = useState([]);
  const [filteredTicks, setFilteredTicks] = useState([]);
  const [selectedAsset, setSelectedAsset] = useState('EURUSD_otc');
  const [customAssetInput, setCustomAssetInput] = useState('');
  const [subscribeError, setSubscribeError] = useState(null);
  const [subscribeStatus, setSubscribeStatus] = useState(null);
  const [subscribeBusy, setSubscribeBusy] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [payoutFilter, setPayoutFilter] = useState('ALL'); // 'ALL', '92%+', '90%+'
  const [activeTab, setActiveTab] = useState('raw'); // 'raw', 'filtered', 'bayesian'
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [activeGates, setActiveGates] = useState({
    bayesian: true,
    volatility: true,
    liquidity: true,
    manipulation: true,
  });

  // Master asset list with payout metadata & live streaming status
  const [assetCatalog, setAssetCatalog] = useState(DEFAULT_FULL_ASSET_CATALOG);
  const [velocityData, setVelocityData] = useState([]);
  const [bayesianMatrix, setBayesianMatrix] = useState([]);
  const [subscribingAsset, setSubscribingAsset] = useState(null);
  const [alertTesting, setAlertTesting] = useState(false);
  const [alertToast, setAlertToast] = useState(null);

  // 1. Zero-Latency Real-Time Server-Sent Events (SSE) Stream
  useEffect(() => {
    let eventSource = null;
    try {
      eventSource = new EventSource(`/api/v1/stream?asset=${selectedAsset}`);

      eventSource.addEventListener('tick', (e) => {
        try {
          const tickData = JSON.parse(e.data);
          if (tickData && tickData.asset === selectedAsset) {
            setRawTicks((prev) => [tickData, ...prev.slice(0, 14)]);
          }
        } catch (parseErr) {
          console.debug('SSE parse error:', parseErr);
        }
      });

      eventSource.onerror = (err) => {
        console.debug('SSE stream standby or reconnecting:', err);
        if (eventSource) {
          eventSource.close();
        }
      };
    } catch (sseErr) {
      console.debug('EventSource not initialized:', sseErr);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [selectedAsset]);

  // 2. Periodic Telemetry & Metric Polling (Fallback & Sync)
  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, 4000);
    return () => clearInterval(timer);
  }, [selectedAsset]);

  const fetchData = async () => {
    try {
      // 1. Telemetry Status
      const resStatus = await fetch('/api/status');
      if (resStatus.ok) {
        const dataStatus = await resStatus.json();
        setTelemetry(dataStatus);
      }

      // 2. Dynamic Asset Catalog & Live Payouts
      try {
        const resAssets = await fetch('/api/v1/assets');
        if (resAssets.ok) {
          const dataAssets = await resAssets.json();
          if (Array.isArray(dataAssets.assets) && dataAssets.assets.length > 0) {
            setAssetCatalog((prev) => {
              const serverMap = new Map(dataAssets.assets.map((a) => [a.symbol, a]));
              const merged = dataAssets.assets.slice();
              for (const item of prev) {
                if (!serverMap.has(item.symbol)) {
                  merged.unshift(item);
                }
              }
              return merged;
            });
          }
        }
      } catch (assetErr) {
        console.debug('Assets endpoint standby:', assetErr);
      }

      // 3. Live Raw Ticks
      const resRaw = await fetch(`/api/v1/ticks/raw?asset=${selectedAsset}&limit=15`);
      if (resRaw.ok) {
        const dataRaw = await resRaw.json();
        setRawTicks(dataRaw.ticks || []);
      }

      // 4. Live Dynamic Velocity & Volatility Timeseries
      try {
        const resVel = await fetch(`/api/v1/ticks/velocity?asset=${selectedAsset}&limit=12`);
        if (resVel.ok) {
          const dataVel = await resVel.json();
          if (Array.isArray(dataVel.points)) {
            setVelocityData(dataVel.points);
          }
        }
      } catch (velErr) {
        console.debug('Velocity endpoint standby:', velErr);
      }

      // 5. Dynamic Filtered Ticks
      const activeGateList = Object.keys(activeGates).filter((k) => activeGates[k]).join(',');
      const resFilt = await fetch(`/api/v1/ticks/filtered?asset=${selectedAsset}&limit=15&gates=${activeGateList}`);
      if (resFilt.ok) {
        const dataFilt = await resFilt.json();
        setFilteredTicks(dataFilt.ticks || []);
      }

      // 6. Live Bayesian Feature Priors Matrix
      try {
        const resPriors = await fetch('/api/v1/priors');
        if (resPriors.ok) {
          const dataPriors = await resPriors.json();
          const priorsObj = dataPriors.priors || dataPriors;
          if (priorsObj && typeof priorsObj === 'object') {
            const matrix = [];
            for (const [key, val] of Object.entries(priorsObj)) {
              if (val && typeof val === 'object') {
                const total = Number(val.total || 0);
                const wins = Number(val.wins || 0);
                const rate = total > 0 ? (wins / total) * 100 : Number(val.win_rate || val.probability || 50);
                matrix.push({
                  category: key.replace(/_/g, ' ').toUpperCase(),
                  win_rate: Number(rate.toFixed(1)),
                  sample: total,
                });
              }
            }
            if (matrix.length > 0) {
              setBayesianMatrix(matrix.slice(0, 8));
            }
          }
        }
      } catch (priorErr) {
        console.debug('Priors endpoint standby:', priorErr);
      }
    } catch (e) {
      console.warn('Telemetry server offline or proxy loading...', e);
    }
  };

  const handleTestAlert = async () => {
    setAlertTesting(true);
    setAlertToast(null);
    try {
      const res = await fetch('/api/v1/alerts/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `🔔 [OTC SNIPER] Live Telemetry Alert: ${selectedAsset} stream active. Buffer size: ${telemetry?.sink?.buffer_size || 0} ticks.`
        }),
      });
      const data = await res.json();
      setAlertToast({
        success: data.delivered,
        message: data.message || 'Alert dispatched.',
      });
    } catch (err) {
      setAlertToast({
        success: false,
        message: 'Could not reach alert dispatch bridge.',
      });
    } finally {
      setAlertTesting(false);
      setTimeout(() => setAlertToast(null), 5000);
    }
  };

  const handleSelectAsset = async (symbol) => {
    setSelectedAsset(symbol);
    setSubscribingAsset(symbol);
    try {
      await fetch('/api/v1/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ asset: symbol }),
      });
      // Optimistically flag asset as live
      setAssetCatalog((prev) =>
        prev.map((item) => (item.symbol === symbol ? { ...item, live: true } : item))
      );
      fetchData();
    } catch (err) {
      console.warn('Auto-subscribe asset error:', err);
    } finally {
      setTimeout(() => setSubscribingAsset(null), 1200);
    }
  };

  const handleSubscribeCustomAsset = async () => {
    setSubscribeError(null);
    setSubscribeStatus(null);

    // Blank / whitespace-only: ignore without runtime error or console noise.
    if (!canSubmitCustomAsset(customAssetInput)) {
      return;
    }

    const ticker = customAssetInput.trim();
    setSubscribeBusy(true);
    try {
      let response;
      try {
        response = await fetch('/api/v1/subscribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ asset: ticker }),
        });
      } catch {
        setSubscribeError('Unable to reach the data agent. Check that the telemetry server is online.');
        return;
      }

      let payload = {};
      try {
        payload = await response.json();
      } catch {
        payload = {};
      }

      if (!response.ok || payload.status !== 'ok' || payload.subscribed !== true) {
        const message =
          payload.message ||
          (response.status === 504
            ? 'Subscription timed out. Try again in a moment.'
            : response.status === 400
              ? 'Invalid asset symbol. Check the ticker and try again.'
              : 'Subscription failed. Selection and catalog were left unchanged.');
        setSubscribeError(message);
        return;
      }

      // Catalog mutation only after confirmed subscription.
      if (!assetCatalog.some((a) => a.symbol === ticker)) {
        setAssetCatalog((prev) => [buildCustomCatalogEntry(ticker), ...prev]);
      }
      setSelectedAsset(ticker);
      setCustomAssetInput('');
      setSubscribeStatus(`Subscribed to ${ticker}`);
      fetchData();
    } finally {
      setSubscribeBusy(false);
    }
  };

  const toggleGate = (gateKey) => {
    setActiveGates((prev) => ({ ...prev, [gateKey]: !prev[gateKey] }));
  };

  const selectedCatalogItem = useMemo(
    () => resolveSelectedAsset(assetCatalog, selectedAsset),
    [assetCatalog, selectedAsset]
  );
  const selectedPayoutLabel = formatPayoutLabel(selectedCatalogItem?.payout);

  // Filter asset catalog by search query & payout tab
  const filteredCatalog = assetCatalog.filter((item) => {
    const matchesSearch =
      item.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch && matchesPayoutFilter(item, payoutFilter);
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <ConnectSSIDModal
        isOpen={isConnectModalOpen}
        onClose={() => setIsConnectModalOpen(false)}
        telemetry={telemetry}
        onSessionUpdated={fetchData}
      />

      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md px-6 py-3.5 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-cyan-600 to-blue-600 rounded-lg text-white shadow-lg shadow-cyan-500/20">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-400 bg-clip-text text-transparent">
                VPS Data Agent Hub
              </h1>
              <span
                className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                  telemetry?.collector?.is_demo === false
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                }`}
              >
                {telemetry?.collector?.is_demo === false ? '● REAL ACCOUNT' : '● DEMO ACCOUNT'}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">Standalone DaaS Microservice & Historical Memory Vault</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Test WhatsApp Alert Button */}
          <button
            onClick={handleTestAlert}
            disabled={alertTesting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition disabled:opacity-50"
            title="Dispatch a test telemetry alert to configured OpenWA phone"
          >
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>{alertTesting ? 'Sending Alert...' : 'Test WhatsApp'}</span>
          </button>

          {/* Connect PO SSID Button */}
          <button
            onClick={() => setIsConnectModalOpen(true)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-mono border transition ${
              telemetry?.collector?.connected
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
                : telemetry?.collector?.ssid_configured
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-300 hover:bg-amber-500/20'
                  : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {telemetry?.collector?.connected ? <Wifi size={14} /> : <WifiOff size={14} />}
            <span className="font-semibold">
              {telemetry?.collector?.connected
                ? 'PO Session Streaming'
                : telemetry?.collector?.ssid_configured
                  ? 'PO Reconnecting...'
                  : 'Connect PO SSID'}
            </span>
          </button>

          <div className="flex items-center gap-2 bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-full text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-emerald-400 font-semibold">GCP BigQuery Connected</span>
          </div>

          <button
            onClick={fetchData}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition"
            title="Refresh Telemetry"
          >
            <RefreshCcw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Alert Toast Popover */}
      {alertToast && (
        <div className="fixed top-16 right-6 z-50 max-w-sm bg-slate-900 border border-slate-700 shadow-2xl rounded-xl p-4 flex items-start gap-3 animate-in fade-in slide-in-from-top-2">
          {alertToast.success ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          ) : (
            <XCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          )}
          <div className="space-y-1 text-xs">
            <p className="font-semibold text-slate-200">
              {alertToast.success ? 'WhatsApp Alert Dispatched' : 'Alert Dispatch Warning'}
            </p>
            <p className="text-slate-400 font-mono">{alertToast.message}</p>
          </div>
        </div>
      )}

      {/* Main Body: Left Sidebar + Workspace Dashboard */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT SIDEBAR: Selectable Asset Drawer */}
        <aside className="w-80 border-r border-slate-800 bg-slate-900/60 flex flex-col flex-shrink-0 font-mono">
          {/* Sidebar Header & Search */}
          <div className="p-4 border-b border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase text-slate-300 flex items-center gap-2">
                <Radio className="w-4 h-4 text-cyan-400" />
                Asset Streams
              </span>
              <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-cyan-400 font-semibold">
                {filteredCatalog.length} Pairs
              </span>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search pair (EUR, ZAR...)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Payout Filter Tabs */}
            <div className="grid grid-cols-3 gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800/80 text-[10px] font-semibold text-center">
              {['ALL', '92%+', '90%+'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setPayoutFilter(tab)}
                  className={`py-1 rounded transition ${
                    payoutFilter === tab ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Asset List Scroll Area */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {filteredCatalog.map((item) => {
              const isSelected = selectedAsset === item.symbol;
              const isSubscribing = subscribingAsset === item.symbol;
              return (
                <div
                  key={item.symbol}
                  onClick={() => handleSelectAsset(item.symbol)}
                  className={`p-3 rounded-lg border transition cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? 'bg-cyan-500/10 border-cyan-500/60 shadow-md shadow-cyan-500/10'
                      : 'bg-slate-950/40 border-slate-800/60 hover:bg-slate-800/40 hover:border-slate-700'
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold ${isSelected ? 'text-cyan-300' : 'text-slate-200'}`}>
                        {item.symbol}
                      </span>
                      {isSubscribing ? (
                        <span className="text-[10px] text-cyan-400 font-mono animate-pulse">syncing...</span>
                      ) : item.live ? (
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" title="Active Wire Subscription"></span>
                      ) : null}
                    </div>
                    <p className="text-[10px] text-slate-500">{item.name}</p>
                  </div>

                  <div className="text-right space-y-1">
                    <span className="inline-block bg-emerald-500/20 text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded">
                      {formatPayoutLabel(item.payout)}
                    </span>
                    <p className="text-[10px] text-slate-400">
                      {item.velocity != null ? `${item.velocity} t/m` : '— t/m'}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Sidebar Footer: Add Custom Ticker */}
          <div className="p-3 border-t border-slate-800 bg-slate-950 space-y-2">
            <span className="text-[10px] font-semibold uppercase text-slate-400 block">Add Custom Stream</span>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="e.g. BTCUSD..."
                value={customAssetInput}
                onChange={(e) => {
                  setCustomAssetInput(e.target.value);
                  if (subscribeError) setSubscribeError(null);
                  if (subscribeStatus) setSubscribeStatus(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleSubscribeCustomAsset();
                  }
                }}
                aria-label="Custom asset ticker"
                aria-invalid={Boolean(subscribeError)}
                aria-describedby={subscribeError ? 'subscribe-error' : subscribeStatus ? 'subscribe-status' : undefined}
                disabled={subscribeBusy}
                className="flex-1 bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 disabled:opacity-60"
              />
              <button
                type="button"
                onClick={handleSubscribeCustomAsset}
                disabled={subscribeBusy || !canSubmitCustomAsset(customAssetInput)}
                className="bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed text-slate-950 px-3 py-1.5 rounded font-bold text-xs transition flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" />
                Add
              </button>
            </div>
            {subscribeError && (
              <p id="subscribe-error" role="alert" className="text-[10px] text-rose-400">
                {subscribeError}
              </p>
            )}
            {subscribeStatus && !subscribeError && (
              <p id="subscribe-status" role="status" className="text-[10px] text-emerald-400">
                {subscribeStatus}
              </p>
            )}
          </div>
        </aside>

        {/* RIGHT WORKSPACE: Main Telemetry & Gating Dashboard */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Asset Info Header Banner */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between shadow-sm">
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-bold text-slate-100 font-mono">{selectedAsset}</h2>
                <span
                  className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-bold px-2.5 py-0.5 rounded-full font-mono"
                  data-testid="selected-payout-badge"
                >
                  {selectedPayoutLabel} Payout
                </span>
                <span className="bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs font-bold px-2.5 py-0.5 rounded-full font-mono">
                  Active Subscription
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono">Historical tick streaming to BigQuery & SQLite fallback vault</p>
            </div>
          </div>

          {/* KPI Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4 shadow-sm">
              <div className="p-3 bg-cyan-500/10 text-cyan-400 rounded-lg">
                <Zap className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs text-slate-400 uppercase font-semibold">Total Ingested Ticks</p>
                <p className="text-2xl font-bold text-slate-100 font-mono">
                  {telemetry?.collector?.total_ticks ?? 0} <span className="text-xs font-normal text-slate-400">ticks</span>
                </p>
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4 shadow-sm">
              <div className="p-3 bg-blue-500/10 text-blue-400 rounded-lg">
                <Activity className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs text-slate-400 uppercase font-semibold">Local Flushed Ticks</p>
                <p className="text-2xl font-bold text-emerald-400 font-mono">
                  {telemetry?.sink?.total_flushed ?? 0} <span className="text-xs font-normal text-slate-400">SQLite</span>
                </p>
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4 shadow-sm">
              <div className="p-3 bg-purple-500/10 text-purple-400 rounded-lg">
                <BarChart3 className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs text-slate-400 uppercase font-semibold">Buffer Queue</p>
                <p className="text-2xl font-bold text-slate-100 font-mono">
                  {telemetry?.sink?.buffer_size ?? 0} <span className="text-xs font-normal text-slate-400">in-flight</span>
                </p>
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4 shadow-sm">
              <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-lg">
                <Database className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs text-slate-400 uppercase font-semibold">GCP Sink Health</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  <p className="text-sm font-bold text-slate-100 font-mono">
                    {telemetry?.sink?.gcp_project_id || 'otc-sniper-prod'}
                  </p>
                </div>
              </div>
            </div>
          </div>


          {/* Bklit Style Area Chart: Tick Stream & Volatility */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-cyan-400" />
                <h2 className="text-lg font-semibold text-slate-200">Live Tick Stream Density & Volatility</h2>
              </div>
              <span className="text-xs font-mono text-slate-400">bklit-ui area-chart overlay</span>
            </div>

            <div className="h-64 w-full">
              {velocityData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={velocityData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorTicks" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                      </linearGradient>
                      <linearGradient id="colorVol" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 12 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 12 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }} />
                    <Area type="monotone" dataKey="ticks_per_min" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#colorTicks)" name="Tick Density (per min)" />
                    <Area type="monotone" dataKey="vol" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorVol)" name="Volatility Score" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 font-mono text-xs gap-2">
                  <Activity className="w-6 h-6 text-slate-600 animate-pulse" />
                  <span>Harvesting live ticks for <code className="text-cyan-400">{selectedAsset}</code>... Points populate as batches are received.</span>
                </div>
              )}
            </div>
          </div>

          {/* Data View Tabs & Dynamic Filter Controls */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
              {/* View Selector Tabs */}
              <div className="flex items-center gap-2 bg-slate-950 p-1 rounded-lg border border-slate-800">
                <button
                  onClick={() => setActiveTab('raw')}
                  className={`px-4 py-2 rounded-md text-xs font-semibold font-mono transition ${
                    activeTab === 'raw' ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Database className="w-3.5 h-3.5" />
                    100% Clean Raw Baseline
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab('filtered')}
                  className={`px-4 py-2 rounded-md text-xs font-semibold font-mono transition ${
                    activeTab === 'filtered' ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Filter className="w-3.5 h-3.5" />
                    Dynamic Filter Overlay
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab('bayesian')}
                  className={`px-4 py-2 rounded-md text-xs font-semibold font-mono transition ${
                    activeTab === 'bayesian' ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <BarChart3 className="w-3.5 h-3.5" />
                    Bayesian Win-Rate Matrix
                  </span>
                </button>
              </div>

              {/* Modular Filter Toggles */}
              {activeTab === 'filtered' && (
                <div className="flex items-center gap-3 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
                  <span className="text-xs font-mono text-slate-400 uppercase">Active Gates:</span>
                  {Object.keys(activeGates).map((gate) => (
                    <button
                      key={gate}
                      onClick={() => toggleGate(gate)}
                      className={`px-2.5 py-1 rounded text-xs font-mono transition ${
                        activeGates[gate]
                          ? 'bg-cyan-500/20 border border-cyan-500/50 text-cyan-300'
                          : 'bg-slate-800 text-slate-500 border border-transparent'
                      }`}
                    >
                      {gate}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Tab 1: Clean Raw Tick Stream Table */}
            {activeTab === 'raw' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Timestamp</th>
                      <th className="py-2.5 px-3">Asset</th>
                      <th className="py-2.5 px-3">Raw Price</th>
                      <th className="py-2.5 px-3">Direction</th>
                      <th className="py-2.5 px-3">Received At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {rawTicks.length > 0 ? (
                      rawTicks.map((t, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/30 transition">
                          <td className="py-2 px-3 text-slate-300">{t.timestamp}</td>
                          <td className="py-2 px-3 font-semibold text-cyan-400">{t.asset}</td>
                          <td className="py-2 px-3 text-slate-100 font-bold">{t.price}</td>
                          <td className="py-2 px-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] ${t.dir === 1 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                              {t.dir === 1 ? 'CALL' : 'PUT'}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-slate-500">{t.received_at}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="5" className="py-6 text-center text-slate-500">
                          No raw ticks loaded yet for <code className="text-cyan-400">{selectedAsset}</code>. Start <code className="text-cyan-400">vps_server.py</code> to stream live ticks.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab 2: Dynamic Filter Overlay Inspection Table */}
            {activeTab === 'filtered' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Timestamp</th>
                      <th className="py-2.5 px-3">Asset</th>
                      <th className="py-2.5 px-3">Price</th>
                      <th className="py-2.5 px-3">Gate Evaluation</th>
                      <th className="py-2.5 px-3">Veto Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {filteredTicks.length > 0 ? (
                      filteredTicks.map((t, idx) => {
                        const evalResult = t.filter_evaluation || {};
                        return (
                          <tr key={idx} className="hover:bg-slate-800/30 transition">
                            <td className="py-2 px-3 text-slate-300">{t.timestamp}</td>
                            <td className="py-2 px-3 font-semibold text-cyan-400">{t.asset}</td>
                            <td className="py-2 px-3 text-slate-100 font-bold">{t.price}</td>
                            <td className="py-2 px-3">
                              {evalResult.passed ? (
                                <span className="inline-flex items-center gap-1 bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded text-[10px] font-semibold">
                                  <CheckCircle2 className="w-3 h-3" /> PASSED ALL GATES
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 bg-rose-500/20 text-rose-400 px-2 py-0.5 rounded text-[10px] font-semibold">
                                  <XCircle className="w-3 h-3" /> VETOED BY GATE
                                </span>
                              )}
                            </td>
                            <td className="py-2 px-3 text-slate-400">
                              {evalResult.veto_reasons && evalResult.veto_reasons.length > 0 ? (
                                <span className="text-amber-400">{evalResult.veto_reasons.join(', ')}</span>
                              ) : (
                                <span className="text-slate-600">None</span>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan="5" className="py-6 text-center text-slate-500">
                          No filtered tick evaluation loaded yet for <code className="text-cyan-400">{selectedAsset}</code>.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab 3: Bayesian Feature Prior Matrix Chart */}
            {activeTab === 'bayesian' && (
              <div className="space-y-4">
                <div className="h-64 w-full">
                  {bayesianMatrix.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={bayesianMatrix} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="category" stroke="#64748b" tick={{ fontSize: 12 }} />
                        <YAxis domain={[30, 90]} stroke="#64748b" tick={{ fontSize: 12 }} />
                        <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }} />
                        <Bar dataKey="win_rate" fill="#06b6d4" radius={[6, 6, 0, 0]} name="Win Rate %" />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-slate-500 font-mono text-xs gap-2">
                      <Database className="w-6 h-6 text-slate-600 animate-pulse" />
                      <span>Awaiting recorded trade outcomes to compute empirical Bayesian feature win-rate priors.</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
