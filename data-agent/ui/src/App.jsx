import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
  Database,
  Activity,
  ShieldCheck,
  Zap,
  Filter,
  BarChart3,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Search,
  Plus,
  Radio,
  Wifi,
  WifiOff,
  Star,
  ChevronDown,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Clock,
  Layers,
  Sparkles,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  DEFAULT_PAYOUT_THRESHOLD,
  QUICK_PAYOUT_PRESETS,
  ASSET_TYPE_OPTIONS,
  DEFAULT_FULL_ASSET_CATALOG,
  buildCustomCatalogEntry,
  canSubmitCustomAsset,
  formatPayoutLabel,
  formatDisplayName,
  matchesFilters,
  resolveAssetClass,
  resolveSelectedAsset,
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
  const [payoutThreshold, setPayoutThreshold] = useState(DEFAULT_PAYOUT_THRESHOLD);
  const [otcOnly, setOtcOnly] = useState(false);
  const [assetTypeFilter, setAssetTypeFilter] = useState('all');
  const [filtersOpen, setFiltersOpen] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [starredAssets, setStarredAssets] = useState(() => {
    try {
      const saved = localStorage.getItem('otc_starred_assets');
      return saved ? JSON.parse(saved) : ['EURUSD_otc', 'GBPUSD_otc', 'GOLD_otc', 'BTCUSD'];
    } catch (err) {
      console.warn('Failed to parse starred assets from localStorage:', err);
      return ['EURUSD_otc', 'GBPUSD_otc', 'GOLD_otc', 'BTCUSD'];
    }
  });

  const [sseConnected, setSseConnected] = useState(false);
  const [activeTab, setActiveTab] = useState('raw'); // 'raw', 'filtered', 'bayesian'
  const [chartMode, setChartMode] = useState('price'); // 'price', 'velocity', 'bayesian'
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
  const [priceHistory, setPriceHistory] = useState([]);

  // Keep latest selected asset in a ref so SSE handlers never use a stale closure
  const selectedAssetRef = useRef(selectedAsset);
  useEffect(() => {
    selectedAssetRef.current = selectedAsset;
  }, [selectedAsset]);

  // Save starred assets to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('otc_starred_assets', JSON.stringify(starredAssets));
    } catch (err) {
      console.warn('Failed to save starred assets to localStorage:', err);
    }
  }, [starredAssets]);

  const toggleStarredAsset = (symbol) => {
    setStarredAssets((prev) =>
      prev.includes(symbol) ? prev.filter((s) => s !== symbol) : [...prev, symbol]
    );
  };

  // 1. Zero-Latency Real-Time Server-Sent Events (SSE) Stream
  useEffect(() => {
    let eventSource = null;
    let reconnectTimer = null;
    let reconnectDelay = 1000;
    let cancelled = false;
    const assetForStream = selectedAsset;

    function connectSSE() {
      if (cancelled) return;
      try {
        eventSource = new EventSource(
          `/api/v1/stream?asset=${encodeURIComponent(assetForStream)}`
        );

        eventSource.addEventListener('connected', () => {
          reconnectDelay = 1000;
          if (!cancelled && selectedAssetRef.current === assetForStream) {
            setSseConnected(true);
          }
        });

        eventSource.addEventListener('tick', (e) => {
          try {
            // Ignore ticks if user already switched away from this stream's asset
            if (selectedAssetRef.current !== assetForStream) return;

            const tickData = JSON.parse(e.data);
            if (!tickData || tickData.asset !== assetForStream) return;

            setRawTicks((prev) => {
              // Drop any leftover ticks from a previous asset
              const sameAsset = prev.filter((t) => t && t.asset === assetForStream);
              return [tickData, ...sameAsset.slice(0, 19)];
            });

            const timeStr = new Date((tickData.timestamp || Date.now() / 1000) * 1000)
              .toISOString()
              .slice(11, 19);
            setPriceHistory((prev) => {
              const updated = [
                ...prev,
                {
                  time: timeStr,
                  price: Number(tickData.price),
                  dir:
                    tickData.dir === 1 || tickData.dir === 'up'
                      ? 'CALL'
                      : tickData.dir === 0 || tickData.dir === 'down'
                        ? 'PUT'
                        : 'NEUTRAL',
                  timestamp: tickData.timestamp,
                },
              ];
              return updated.slice(-30);
            });
          } catch (parseErr) {
            console.debug('SSE parse error:', parseErr);
          }
        });

        eventSource.onerror = () => {
          if (cancelled) return;
          setSseConnected(false);
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          console.debug(`SSE disconnected. Reconnecting in ${reconnectDelay / 1000}s...`);
          reconnectTimer = setTimeout(() => {
            reconnectDelay = Math.min(reconnectDelay * 2, 8000);
            connectSSE();
          }, reconnectDelay);
        };
      } catch (sseErr) {
        setSseConnected(false);
        console.warn('EventSource not initialized:', sseErr);
      }
    }

    connectSSE();

    return () => {
      cancelled = true;
      setSseConnected(false);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
    };
  }, [selectedAsset]);

  const fetchData = useCallback(async (silent = false) => {
    if (!silent) setIsRefreshing(true);
    const asset = selectedAssetRef.current;
    const activeGateList = Object.keys(activeGates).filter((k) => activeGates[k]).join(',');

    try {
      const endpoints = [
        { name: 'status', url: '/api/status' },
        { name: 'assets', url: '/api/v1/assets' },
        { name: 'rawTicks', url: `/api/v1/ticks/raw?asset=${encodeURIComponent(asset)}&limit=20` },
        { name: 'velocity', url: `/api/v1/ticks/velocity?asset=${encodeURIComponent(asset)}&limit=16` },
        {
          name: 'filteredTicks',
          url: `/api/v1/ticks/filtered?asset=${encodeURIComponent(asset)}&limit=15&gates=${activeGateList}`,
        },
        { name: 'priors', url: '/api/v1/priors' },
      ];

      const results = await Promise.allSettled(
        endpoints.map((ep) =>
          fetch(ep.url).then((res) => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
          })
        )
      );

      // Drop late responses from a previous asset selection
      if (selectedAssetRef.current !== asset) {
        return;
      }

      const statusRes = results[0];
      const assetsRes = results[1];
      const rawTicksRes = results[2];
      const velocityRes = results[3];
      const filteredTicksRes = results[4];
      const priorsRes = results[5];

      // 1. Telemetry Status
      if (statusRes.status === 'fulfilled') {
        setTelemetry(statusRes.value);
      } else {
        console.warn('Status endpoint failed:', statusRes.reason);
      }

      // 2. Dynamic Asset Catalog & Live Payouts
      if (assetsRes.status === 'fulfilled') {
        const dataAssets = assetsRes.value;
        if (dataAssets && Array.isArray(dataAssets.assets) && dataAssets.assets.length > 0) {
          setAssetCatalog((prev) => {
            const catalogMap = new Map();
            prev.forEach((item) => catalogMap.set(item.symbol, item));
            dataAssets.assets.forEach((serverItem) => {
              const existing = catalogMap.get(serverItem.symbol);
              catalogMap.set(serverItem.symbol, {
                ...existing,
                ...serverItem,
              });
            });
            return Array.from(catalogMap.values());
          });
        }
      } else {
        console.warn('Assets endpoint failed:', assetsRes.reason);
      }

      // 3. Live Raw Ticks — always accept polled ticks for the focused asset.
      // Previous logic skipped poll updates whenever SSE was connected, which froze
      // the tick list after asset switches (old ticks stayed, new asset never loaded).
      if (rawTicksRes.status === 'fulfilled') {
        const dataRaw = rawTicksRes.value;
        const ticks = ((dataRaw && dataRaw.ticks) || []).filter(
          (t) => !t?.asset || t.asset === asset
        );

        setRawTicks((prev) => {
          const prevSameAsset = prev.filter((t) => t && t.asset === asset);
          // If SSE already has fresher live ticks, keep them and only backfill gaps
          if (prevSameAsset.length > 0 && ticks.length > 0) {
            const newestLive = Number(prevSameAsset[0]?.timestamp || 0);
            const newestPoll = Number(ticks[0]?.timestamp || 0);
            if (newestLive >= newestPoll) {
              return prevSameAsset.slice(0, 20);
            }
          }
          if (ticks.length > 0) return ticks.slice(0, 20);
          return prevSameAsset;
        });

        if (ticks.length > 0) {
          setPriceHistory((prev) => {
            // Seed chart only when empty (fresh asset switch) — don't clobber live SSE series
            if (prev.length > 0) return prev;
            const seed = [...ticks].reverse().map((t) => ({
              time: new Date((t.timestamp || Date.now() / 1000) * 1000)
                .toISOString()
                .slice(11, 19),
              price: Number(t.price),
              dir: t.dir === 'up' || t.dir === 1 ? 'CALL' : 'PUT',
              timestamp: t.timestamp,
            }));
            return seed.slice(-30);
          });
        }
      } else {
        console.warn('Raw ticks endpoint failed:', rawTicksRes.reason);
      }

      // 4. Live Dynamic Velocity & Volatility — always refresh for focused asset
      if (velocityRes.status === 'fulfilled') {
        const dataVel = velocityRes.value;
        const points = dataVel && Array.isArray(dataVel.points) ? dataVel.points : [];
        setVelocityData(points);
      } else {
        setVelocityData([]);
        console.warn('Velocity endpoint failed:', velocityRes.reason);
      }

      // 5. Dynamic Filtered Ticks
      if (filteredTicksRes.status === 'fulfilled') {
        const dataFilt = filteredTicksRes.value;
        const filtTicks = ((dataFilt && dataFilt.ticks) || []).filter(
          (t) => !t?.asset || t.asset === asset
        );
        setFilteredTicks(filtTicks);
      } else {
        console.warn('Filtered ticks endpoint failed:', filteredTicksRes.reason);
      }

      // 6. Live Bayesian Feature Priors Matrix
      if (priorsRes.status === 'fulfilled') {
        const dataPriors = priorsRes.value;
        const priorsObj = (dataPriors && (dataPriors.priors || dataPriors)) || {};
        const counts = priorsObj.feature_counts || (typeof priorsObj === 'object' ? priorsObj : {});
        const matrix = [];

        for (const [key, val] of Object.entries(counts)) {
          if (val && typeof val === 'object') {
            const wins = Number(val.win ?? val.wins ?? 0);
            const losses = Number(val.loss ?? val.losses ?? 0);
            const total = wins + losses > 0 ? wins + losses : Number(val.total ?? 0);
            const rate =
              total > 0 ? (wins / total) * 100 : Number(val.win_rate ?? val.probability ?? 50);

            matrix.push({
              category: key.replace(/_/g, ' ').toUpperCase(),
              win_rate: Number(rate.toFixed(1)),
              sample: total,
              wins,
              losses,
            });
          }
        }

        if (matrix.length > 0) {
          matrix.sort((a, b) => b.sample - a.sample);
          setBayesianMatrix(matrix.slice(0, 10));
        }
      } else {
        console.warn('Priors endpoint failed:', priorsRes.reason);
      }
    } catch (e) {
      console.warn('Telemetry server offline or proxy loading...', e);
    } finally {
      if (!silent && selectedAssetRef.current === asset) setIsRefreshing(false);
    }
  }, [activeGates]);

  // 2. Periodic Telemetry & Metric Polling (Fallback & Sync)
  useEffect(() => {
    fetchData(false);
    const timer = setInterval(() => fetchData(true), 4000);
    return () => clearInterval(timer);
  }, [selectedAsset, fetchData]);

  const handleTestAlert = async () => {
    setAlertTesting(true);
    setAlertToast(null);
    try {
      const res = await fetch('/api/v1/alerts/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `🔔 [OTC SNIPER] Live Telemetry Alert: ${selectedAsset} stream active. Buffer: ${telemetry?.sink?.buffer_size || 0} ticks.`
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
    if (selectedAsset === symbol) return;

    // Immediately clear focused-asset UI so old ticks/charts never linger
    setSelectedAsset(symbol);
    selectedAssetRef.current = symbol;
    setRawTicks([]);
    setFilteredTicks([]);
    setPriceHistory([]);
    setVelocityData([]);
    setSseConnected(false);
    setSubscribingAsset(symbol);

    try {
      const response = await fetch('/api/v1/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ asset: symbol }),
      });
      let payload = {};
      try {
        payload = await response.json();
      } catch {
        payload = {};
      }
      if (!response.ok || payload.status !== 'ok') {
        console.warn('Auto-subscribe asset rejected:', payload.message || response.status);
      } else {
        setAssetCatalog((prev) =>
          prev.map((item) => (item.symbol === symbol ? { ...item, live: true } : item))
        );
      }
      // Force a fresh poll for the newly selected asset (ticks + velocity)
      await fetchData(true);
    } catch (err) {
      console.warn('Auto-subscribe asset error:', err);
    } finally {
      setTimeout(() => setSubscribingAsset(null), 1200);
    }
  };

  const handleSubscribeCustomAsset = async () => {
    setSubscribeError(null);
    setSubscribeStatus(null);

    if (!canSubmitCustomAsset(customAssetInput)) return;

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
        setSubscribeError('Unable to reach telemetry server.');
        return;
      }

      let payload = {};
      try {
        payload = await response.json();
      } catch { }

      if (!response.ok || payload.status !== 'ok' || payload.subscribed !== true) {
        setSubscribeError(payload.message || 'Subscription failed.');
        return;
      }

      if (!assetCatalog.some((a) => a.symbol === ticker)) {
        setAssetCatalog((prev) => [buildCustomCatalogEntry(ticker), ...prev]);
      }
      // Clear previous asset UI before focusing the custom ticker
      setRawTicks([]);
      setFilteredTicks([]);
      setPriceHistory([]);
      setVelocityData([]);
      setSseConnected(false);
      setSelectedAsset(ticker);
      selectedAssetRef.current = ticker;
      setCustomAssetInput('');
      setSubscribeStatus(`Subscribed to ${ticker}`);
      await fetchData(true);
    } finally {
      setSubscribeBusy(false);
    }
  };

  const toggleGate = (gateKey) => {
    setActiveGates((prev) => ({ ...prev, [gateKey]: !prev[gateKey] }));
  };

  const selectedCatalogItem = useMemo(
    () => resolveSelectedAsset(assetCatalog, selectedAsset) || { symbol: selectedAsset, name: selectedAsset, payout: 92, category: 'Currencies' },
    [assetCatalog, selectedAsset]
  );
  const selectedPayoutLabel = formatPayoutLabel(selectedCatalogItem?.payout);
  const selectedClass = resolveAssetClass(selectedCatalogItem);
  const latestTick = rawTicks[0] || null;

  // Filter asset catalog according to LeftSidebar.jsx rules
  const filteredCatalog = useMemo(() => {
    return assetCatalog
      .filter((item) =>
        matchesFilters(item, {
          searchQuery,
          payoutThreshold,
          otcOnly,
          assetTypeFilter,
        })
      )
      .sort((a, b) => {
        const pA = Number(a.payout ?? 0);
        const pB = Number(b.payout ?? 0);
        if (pB !== pA) return pB - pA;
        return a.symbol.localeCompare(b.symbol);
      });
  }, [assetCatalog, searchQuery, payoutThreshold, otcOnly, assetTypeFilter]);

  const starredList = useMemo(
    () => filteredCatalog.filter((item) => starredAssets.includes(item.symbol)),
    [filteredCatalog, starredAssets]
  );

  const unstarredList = useMemo(
    () => filteredCatalog.filter((item) => !starredAssets.includes(item.symbol)),
    [filteredCatalog, starredAssets]
  );

  // Active subscribed assets list for quick focus ribbon
  const subscribedAssetsList = useMemo(() => {
    return assetCatalog.filter((item) => item.live || telemetry?.collector?.subscribed_assets?.includes(item.symbol));
  }, [assetCatalog, telemetry]);

  // Dynamic price bounds for live price chart
  const priceMinMax = useMemo(() => {
    if (priceHistory.length === 0) return { min: 0, max: 1 };
    const prices = priceHistory.map((p) => p.price);
    const minP = Math.min(...prices);
    const maxP = Math.max(...prices);
    const spread = (maxP - minP) || (minP * 0.0002) || 0.0001;
    return {
      min: Number((minP - spread * 0.2).toFixed(5)),
      max: Number((maxP + spread * 0.2).toFixed(5)),
    };
  }, [priceHistory]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans select-none">
      <ConnectSSIDModal
        isOpen={isConnectModalOpen}
        onClose={() => setIsConnectModalOpen(false)}
        telemetry={telemetry}
        onSessionUpdated={() => fetchData(false)}
      />

      {/* Top Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/90 backdrop-blur-md px-6 py-3 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-cyan-600 via-sky-500 to-blue-600 rounded-xl text-white shadow-lg shadow-cyan-500/20">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-black tracking-tight bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-400 bg-clip-text text-transparent">
                VPS Data Agent Hub
              </h1>
              <span
                className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${telemetry?.collector?.is_demo === false
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                  }`}
              >
                {telemetry?.collector?.is_demo === false ? '● REAL ACCOUNT' : '● DEMO ACCOUNT'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">Standalone DaaS Streaming & Bayesian Telemetry Microservice</p>
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
            <span>{alertTesting ? 'Sending...' : 'Test WhatsApp'}</span>
          </button>

          {/* Connect PO SSID Button */}
          <button
            onClick={() => setIsConnectModalOpen(true)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-mono border transition shadow-sm ${telemetry?.collector?.connected
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
                : telemetry?.collector?.ssid_configured
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-300 hover:bg-amber-500/20'
                  : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
              }`}
          >
            {telemetry?.collector?.connected ? <Wifi size={14} /> : <WifiOff size={14} />}
            <span className="font-semibold">
              {telemetry?.collector?.connected
                ? 'PO SSID Connected'
                : telemetry?.collector?.ssid_configured
                  ? 'PO Reconnecting...'
                  : 'Connect PO SSID'}
            </span>
          </button>

          <div className="flex items-center gap-2 bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-full text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-emerald-400 font-semibold">GCP Sink Active</span>
          </div>

          <button
            onClick={() => fetchData(false)}
            disabled={isRefreshing}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition disabled:opacity-50"
            title="Refresh All Telemetry & Assets"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
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
        {/* LEFT SIDEBAR: Identical filter system to LeftSidebar.jsx */}
        <aside className="w-[260px] border-r border-slate-800/80 bg-slate-900/70 flex flex-col shrink-0 font-sans">
          {/* Search & Refresh Bar */}
          <div className="p-3 border-b border-slate-800/80 space-y-2.5">
            <div className="flex items-center gap-1.5">
              <div className="relative flex-1 group">
                <Search
                  size={13}
                  className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-cyan-400 transition-colors"
                />
                <input
                  type="text"
                  placeholder="Search assets..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-2 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500 uppercase font-mono transition"
                />
              </div>

              <button
                onClick={() => fetchData(false)}
                disabled={isRefreshing}
                className="p-2 bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg border border-slate-700/60 transition"
                title="Refresh Asset Catalog & Payouts"
              >
                <RefreshCw size={12} className={isRefreshing ? 'animate-spin text-cyan-400' : ''} />
              </button>
            </div>

            {/* Collapsible Filter Panel */}
            <div className="rounded-xl border border-slate-800 bg-slate-950/70 overflow-hidden">
              <button
                type="button"
                onClick={() => setFiltersOpen((prev) => !prev)}
                className="flex w-full items-center justify-between p-2.5 text-left hover:bg-slate-900/40 transition"
              >
                <div className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wider text-slate-400">
                  <Filter size={11} className="text-cyan-400" />
                  Asset Filters
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded bg-cyan-500/10 border border-cyan-500/30 px-1.5 py-0.5 text-[9px] font-black text-cyan-300 font-mono">
                    {payoutThreshold}%+
                  </span>
                  <ChevronDown size={12} className={`text-slate-500 transition-transform ${filtersOpen ? 'rotate-180' : 'rotate-0'}`} />
                </div>
              </button>

              {filtersOpen && (
                <div className="border-t border-slate-800/80 p-2.5 space-y-2.5">
                  {/* Payout Threshold Presets Grid */}
                  <div className="grid grid-cols-3 gap-1">
                    {QUICK_PAYOUT_PRESETS.map((preset) => (
                      <button
                        key={preset.value}
                        onClick={() => setPayoutThreshold(preset.value)}
                        className={`rounded py-1 text-[9px] font-black font-mono uppercase tracking-wider transition ${payoutThreshold === preset.value
                            ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm shadow-cyan-500/20'
                            : 'bg-slate-900/80 text-slate-400 hover:text-slate-200 border border-slate-800'
                          }`}
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>

                  {/* OTC Only Switch */}
                  <div className="flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-900/50 p-2">
                    <div>
                      <p className="text-[9px] font-black uppercase tracking-wider text-slate-400">OTC Only</p>
                      <p className="text-[8px] font-bold uppercase text-slate-500">{otcOnly ? 'OTC PAIRS' : 'ALL MARKETS'}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setOtcOnly((prev) => !prev)}
                      className={`relative inline-flex h-4.5 w-8 items-center rounded-full transition-colors ${otcOnly ? 'bg-cyan-500' : 'bg-slate-800'
                        }`}
                    >
                      <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${otcOnly ? 'translate-x-4' : 'translate-x-0.5'}`} />
                    </button>
                  </div>

                  {/* Asset Category Chips Grid */}
                  <div className="grid grid-cols-3 gap-1">
                    {ASSET_TYPE_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => setAssetTypeFilter(opt.value)}
                        className={`rounded py-1 text-[8px] font-black font-mono uppercase tracking-wider transition ${assetTypeFilter === opt.value
                            ? 'bg-cyan-500/20 border border-cyan-500/50 text-cyan-300'
                            : 'bg-slate-900/60 text-slate-500 hover:text-slate-300 border border-slate-800/60'
                          }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Scrollable Asset List */}
          <div className="flex-1 overflow-y-auto p-2 space-y-3 font-mono">
            {/* Quick Select / Starred Assets */}
            {starredList.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 px-2 py-1 mb-1 text-[10px] font-bold uppercase text-amber-400 bg-amber-500/5 rounded border border-amber-500/10">
                  <Star size={10} className="fill-amber-400" />
                  <span>Quick Select ({starredList.length})</span>
                </div>
                <div className="space-y-1">
                  {starredList.map((item) => (
                    <AssetCard
                      key={item.symbol}
                      item={item}
                      isSelected={selectedAsset === item.symbol}
                      isSubscribing={subscribingAsset === item.symbol}
                      isStarred={true}
                      onSelect={() => handleSelectAsset(item.symbol)}
                      onToggleStar={() => toggleStarredAsset(item.symbol)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Main Asset List */}
            <div>
              <div className="flex items-center justify-between px-2 py-1 mb-1 text-[10px] font-bold uppercase text-slate-400">
                <span className="flex items-center gap-1.5">
                  <Radio size={11} className="text-cyan-400" />
                  All Pairs ({unstarredList.length})
                </span>
                <span className="text-[9px] text-slate-500 font-normal">SSID Payouts</span>
              </div>
              <div className="space-y-1">
                {unstarredList.map((item) => (
                  <AssetCard
                    key={item.symbol}
                    item={item}
                    isSelected={selectedAsset === item.symbol}
                    isSubscribing={subscribingAsset === item.symbol}
                    isStarred={false}
                    onSelect={() => handleSelectAsset(item.symbol)}
                    onToggleStar={() => toggleStarredAsset(item.symbol)}
                  />
                ))}
              </div>
              {filteredCatalog.length === 0 && (
                <div className="p-6 text-center text-slate-500 text-xs">
                  No assets match current filters.
                </div>
              )}
            </div>
          </div>

          {/* Footer: Add Custom Stream */}
          <div className="p-3 border-t border-slate-800/80 bg-slate-950 space-y-1.5">
            <span className="text-[10px] font-black uppercase text-slate-500 tracking-wider block font-mono">Custom Ticker</span>
            <div className="flex gap-1.5">
              <input
                type="text"
                placeholder="e.g. SOLUSD..."
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
                disabled={subscribeBusy}
                className="flex-1 bg-slate-900 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 uppercase font-mono focus:outline-none focus:border-cyan-500"
              />
              <button
                type="button"
                onClick={handleSubscribeCustomAsset}
                disabled={subscribeBusy || !canSubmitCustomAsset(customAssetInput)}
                className="bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 disabled:text-slate-600 text-slate-950 px-2.5 py-1 rounded font-bold text-xs transition flex items-center gap-1"
              >
                <Plus size={13} />
                Add
              </button>
            </div>
            {subscribeError && <p className="text-[10px] text-rose-400 font-mono">{subscribeError}</p>}
            {subscribeStatus && <p className="text-[10px] text-emerald-400 font-mono">{subscribeStatus}</p>}
          </div>
        </aside>

        {/* RIGHT WORKSPACE: Focused Asset Header & Real-Time Charts */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* FOCUSED SELECTED ASSET HERO CARD with LABELED BADGES */}
          <div className="bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-slate-950 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden">
            <div className="absolute right-0 top-0 w-96 h-full bg-gradient-to-l from-cyan-500/5 to-transparent pointer-events-none" />

            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="text-3xl font-black text-slate-100 font-mono tracking-tight flex items-center gap-2">
                    {selectedAsset}
                    {selectedAsset.toLowerCase().includes('_otc') && (
                      <span className="text-xs bg-amber-500/10 border border-amber-500/30 text-amber-400 font-bold px-2 py-0.5 rounded uppercase">
                        OTC Pair
                      </span>
                    )}
                  </h2>

                  {/* Labeled Badges */}
                  <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-black px-3 py-1 rounded-full font-mono shadow-sm">
                    {selectedPayoutLabel} Payout
                  </span>

                  <span className="bg-sky-500/10 text-sky-300 border border-sky-500/30 text-xs font-bold px-2.5 py-1 rounded-full font-mono uppercase">
                    {selectedClass}
                  </span>

                  <span className={`border text-xs font-bold px-2.5 py-1 rounded-full font-mono flex items-center gap-1.5 ${sseConnected
                      ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
                      : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                    }`}>
                    <span className={`w-2 h-2 rounded-full ${sseConnected ? 'bg-cyan-400 animate-pulse' : 'bg-rose-400'}`} />
                    {sseConnected ? 'SSE Stream Active' : 'SSE Stream Offline'}
                  </span>
                </div>

                <p className="text-xs text-slate-400 font-mono flex items-center gap-3">
                  <span>Display Name: <strong className="text-slate-200">{formatDisplayName(selectedAsset)}</strong></span>
                  <span>•</span>
                  <span>Ingestion Channel: <strong className="text-cyan-400">changeSymbol({selectedAsset}, 1)</strong></span>
                </p>
              </div>

              {/* Real-time Price & Direction Tile */}
              <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl px-4 py-3 min-w-[200px] text-right font-mono space-y-1">
                <p className="text-[10px] text-slate-500 uppercase font-bold">Latest Tick Price</p>
                <div className="flex items-center justify-end gap-2">
                  {latestTick?.dir === 'up' || latestTick?.dir === 1 ? (
                    <TrendingUp className="w-5 h-5 text-emerald-400" />
                  ) : latestTick?.dir === 'down' || latestTick?.dir === 0 ? (
                    <TrendingDown className="w-5 h-5 text-rose-400" />
                  ) : (
                    <Activity className="w-5 h-5 text-cyan-400" />
                  )}
                  <span className="text-2xl font-black text-slate-100">
                    {latestTick ? latestTick.price : '—'}
                  </span>
                </div>
                <p className="text-[10px] text-slate-400">
                  {latestTick?.received_at ? new Date(latestTick.received_at * 1000).toLocaleTimeString() : 'Awaiting ticks'}
                </p>
              </div>
            </div>

            {/* Quick Subscribed Asset Chips Ribbon */}
            <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center gap-2 overflow-x-auto custom-scrollbar">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono shrink-0 flex items-center gap-1">
                <Layers size={11} /> Quick Switch:
              </span>
              {subscribedAssetsList.map((item) => {
                const isSelected = selectedAsset === item.symbol;
                return (
                  <button
                    key={item.symbol}
                    onClick={() => handleSelectAsset(item.symbol)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition flex items-center gap-1.5 shrink-0 ${isSelected
                        ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20 font-black'
                        : 'bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-800'
                      }`}
                  >
                    <span>{item.symbol}</span>
                    <span className={`text-[10px] px-1 py-0.2 rounded ${isSelected ? 'bg-slate-900/80 text-cyan-300' : 'text-emerald-400'}`}>
                      {item.payout ? `${item.payout}%` : ''}
                    </span>
                  </button>
                );
              })}
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

          {/* REAL-TIME CHARTS SECTION */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-cyan-400" />
                <h2 className="text-lg font-bold text-slate-200">
                  {chartMode === 'price' && `Live Real-Time Price Action: ${selectedAsset}`}
                  {chartMode === 'velocity' && `Tick Stream Density & Volatility Score`}
                  {chartMode === 'bayesian' && `Empirical Bayesian Win-Rate Prior Matrix`}
                </h2>
              </div>

              {/* Chart Mode Switcher Buttons */}
              <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 font-mono text-xs">
                <button
                  onClick={() => setChartMode('price')}
                  className={`px-3 py-1.5 rounded-md font-bold transition ${chartMode === 'price'
                      ? 'bg-cyan-500 text-slate-950 shadow-sm shadow-cyan-500/20'
                      : 'text-slate-400 hover:text-slate-200'
                    }`}
                >
                  Live Price Stream
                </button>

                <button
                  onClick={() => setChartMode('velocity')}
                  className={`px-3 py-1.5 rounded-md font-bold transition ${chartMode === 'velocity'
                      ? 'bg-cyan-500 text-slate-950 shadow-sm shadow-cyan-500/20'
                      : 'text-slate-400 hover:text-slate-200'
                    }`}
                >
                  Density & Volatility
                </button>

                <button
                  onClick={() => setChartMode('bayesian')}
                  className={`px-3 py-1.5 rounded-md font-bold transition ${chartMode === 'bayesian'
                      ? 'bg-cyan-500 text-slate-950 shadow-sm shadow-cyan-500/20'
                      : 'text-slate-400 hover:text-slate-200'
                    }`}
                >
                  Bayesian Matrix
                </button>
              </div>
            </div>

            {/* CHART 1: Real-Time Price Action Area Chart */}
            {chartMode === 'price' && (
              <div className="h-[280px] w-full min-h-[280px]">
                {priceHistory.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280} minWidth={100} minHeight={280}>
                    <AreaChart data={priceHistory} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                      <defs>
                        <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                      <YAxis
                        domain={[priceMinMax.min, priceMinMax.max]}
                        stroke="#64748b"
                        tick={{ fontSize: 11 }}
                        orientation="right"
                        tickFormatter={(v) => Number(v).toFixed(4)}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          borderColor: '#334155',
                          borderRadius: '8px',
                          color: '#f8fafc',
                          fontFamily: 'monospace',
                        }}
                        formatter={(val) => [Number(val).toFixed(5), 'Price']}
                      />
                      <Area
                        type="monotone"
                        dataKey="price"
                        stroke="#06b6d4"
                        strokeWidth={2.5}
                        fillOpacity={1}
                        fill="url(#priceGradient)"
                        isAnimationActive={false}
                        name="Live Price"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-slate-500 font-mono text-xs gap-2">
                    <Activity className="w-6 h-6 text-cyan-500 animate-pulse" />
                    <span>Streaming live ticks for <code className="text-cyan-400 font-bold">{selectedAsset}</code> via Pocket Option SSID...</span>
                  </div>
                )}
              </div>
            )}

            {/* CHART 2: Velocity & Sigmoid Liquidity Area Chart */}
            {chartMode === 'velocity' && (
              <div className="h-[280px] w-full min-h-[280px]">
                {velocityData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280} minWidth={100} minHeight={280}>
                    <AreaChart data={velocityData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorTicks" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="colorLiq" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="colorVol" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          borderColor: '#334155',
                          borderRadius: '8px',
                          color: '#f8fafc',
                          fontFamily: 'monospace',
                        }}
                        formatter={(val, name, item) => {
                          if (name === 'Sigmoid Liquidity %') {
                            const lvl = item.payload.liquidity_level || 'MEDIUM';
                            return [`${val}% [${lvl}]`, name];
                          }
                          if (name === 'Tick Density (t/m)') {
                            return [`${val} t/min`, name];
                          }
                          return [val, name];
                        }}
                      />
                      <Area type="monotone" dataKey="ticks_per_min" stroke="#06b6d4" strokeWidth={1.5} fillOpacity={1} fill="url(#colorTicks)" name="Tick Density (t/m)" isAnimationActive={false} />
                      <Area type="monotone" dataKey="liquidity_score" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorLiq)" name="Sigmoid Liquidity %" isAnimationActive={false} />
                      <Area type="monotone" dataKey="vol" stroke="#3b82f6" strokeWidth={1.5} fillOpacity={1} fill="url(#colorVol)" name="Volatility Score" isAnimationActive={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-slate-500 font-mono text-xs gap-2">
                    <Activity className="w-6 h-6 text-slate-600 animate-pulse" />
                    <span>Aggregating density timeseries for <code className="text-cyan-400 font-bold">{selectedAsset}</code>...</span>
                  </div>
                )}
              </div>
            )}

            {/* CHART 3: Empirical Bayesian Prior Win-Rate Bar Chart */}
            {chartMode === 'bayesian' && (
              <div className="h-[280px] w-full min-h-[280px]">
                {bayesianMatrix.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280} minWidth={100} minHeight={280}>
                    <BarChart data={bayesianMatrix} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="category" stroke="#64748b" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" />
                      <YAxis domain={[30, 90]} stroke="#64748b" tick={{ fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc', fontFamily: 'monospace' }}
                        formatter={(val, name, item) => [
                          `${val}% (Samples: ${item.payload.sample}, Wins: ${item.payload.wins})`,
                          'Empirical Win Rate'
                        ]}
                      />
                      <Bar dataKey="win_rate" fill="#06b6d4" radius={[6, 6, 0, 0]} name="Win Rate %" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-slate-500 font-mono text-xs gap-2">
                    <Database className="w-6 h-6 text-slate-600 animate-pulse" />
                    <span>Reading empirical Bayesian priors from memory store...</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Data View Tabs & Dynamic Filter Controls */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
              {/* View Selector Tabs */}
              <div className="flex items-center gap-2 bg-slate-950 p-1 rounded-lg border border-slate-800">
                <button
                  onClick={() => setActiveTab('raw')}
                  className={`px-4 py-2 rounded-md text-xs font-semibold font-mono transition ${activeTab === 'raw' ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20' : 'text-slate-400 hover:text-slate-200'
                    }`}
                >
                  <span className="flex items-center gap-2">
                    <Database className="w-3.5 h-3.5" />
                    Clean Raw Baseline ({rawTicks.length})
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab('filtered')}
                  className={`px-4 py-2 rounded-md text-xs font-semibold font-mono transition ${activeTab === 'filtered' ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20' : 'text-slate-400 hover:text-slate-200'
                    }`}
                >
                  <span className="flex items-center gap-2">
                    <Filter className="w-3.5 h-3.5" />
                    Dynamic Filter Overlay
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab('bayesian')}
                  className={`px-4 py-2 rounded-md text-xs font-semibold font-mono transition ${activeTab === 'bayesian' ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20' : 'text-slate-400 hover:text-slate-200'
                    }`}
                >
                  <span className="flex items-center gap-2">
                    <BarChart3 className="w-3.5 h-3.5" />
                    Bayesian Matrix ({bayesianMatrix.length})
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
                      className={`px-2.5 py-1 rounded text-xs font-mono transition ${activeGates[gate]
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
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${t.dir === 1 || t.dir === 'up'
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : 'bg-rose-500/20 text-rose-300'
                              }`}>
                              {t.dir === 1 || t.dir === 'up' ? 'CALL' : 'PUT'}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-slate-500">
                            {t.received_at ? new Date(t.received_at * 1000).toLocaleTimeString() : '—'}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="5" className="py-6 text-center text-slate-500">
                          No raw ticks loaded yet for <code className="text-cyan-400 font-bold">{selectedAsset}</code>. Start <code className="text-cyan-400 font-bold">vps_server.py</code> to stream live ticks.
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
                          No filtered tick evaluation loaded yet for <code className="text-cyan-400 font-bold">{selectedAsset}</code>.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab 3: Bayesian Prior Matrix Table */}
            {activeTab === 'bayesian' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Feature Category</th>
                      <th className="py-2.5 px-3">Sample Count</th>
                      <th className="py-2.5 px-3">Wins</th>
                      <th className="py-2.5 px-3">Losses</th>
                      <th className="py-2.5 px-3">Empirical Win Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {bayesianMatrix.length > 0 ? (
                      bayesianMatrix.map((item, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/30 transition">
                          <td className="py-2 px-3 font-semibold text-cyan-300">{item.category}</td>
                          <td className="py-2 px-3 text-slate-200">{item.sample.toLocaleString()}</td>
                          <td className="py-2 px-3 text-emerald-400 font-bold">{item.wins.toLocaleString()}</td>
                          <td className="py-2 px-3 text-rose-400 font-bold">{item.losses.toLocaleString()}</td>
                          <td className="py-2 px-3">
                            <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                              {item.win_rate}%
                            </span>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="5" className="py-6 text-center text-slate-500">
                          No Bayesian feature priors recorded yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

function AssetCard({ item, isSelected, isSubscribing, isStarred, onSelect, onToggleStar }) {
  const payoutLabel = item.payout != null ? `${item.payout}%` : '—%';
  const isOTC = item.symbol.toLowerCase().includes('_otc');

  return (
    <div
      onClick={onSelect}
      className={`p-2.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between select-none ${isSelected
          ? 'bg-cyan-500/10 border-cyan-500/60 shadow-md shadow-cyan-500/10'
          : 'bg-slate-950/40 border-slate-800/60 hover:bg-slate-800/40 hover:border-slate-700'
        }`}
    >
      <div className="flex items-center gap-2 overflow-hidden flex-1">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleStar();
          }}
          className="p-1 text-slate-600 hover:text-amber-400 transition shrink-0"
          title={isStarred ? 'Unstar asset' : 'Star asset'}
        >
          <Star size={12} className={isStarred ? 'text-amber-400 fill-amber-400' : 'text-slate-600'} />
        </button>

        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className={`text-xs font-bold truncate ${isSelected ? 'text-cyan-300' : 'text-slate-200'}`}>
              {item.symbol}
            </span>
            {isOTC && (
              <span className="text-[8px] font-bold px-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                OTC
              </span>
            )}
            {isSubscribing ? (
              <span className="text-[9px] text-cyan-400 animate-pulse">syncing...</span>
            ) : item.live ? (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" title="Active Wire Stream" />
            ) : null}
          </div>
          <p className="text-[9px] text-slate-500 truncate">{item.name || item.symbol}</p>
        </div>
      </div>

      <div className="text-right pl-2 shrink-0">
        <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${isSelected
            ? 'bg-cyan-500 text-slate-950 font-black'
            : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
          }`}>
          {payoutLabel}
        </span>
      </div>
    </div>
  );
}
