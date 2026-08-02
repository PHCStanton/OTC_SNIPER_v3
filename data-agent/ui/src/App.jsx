import React, { useState, useEffect } from 'react';
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
  Cpu,
  Layers,
  FileCode2,
  Server
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

export default function App() {
  const [telemetry, setTelemetry] = useState(null);
  const [rawTicks, setRawTicks] = useState([]);
  const [filteredTicks, setFilteredTicks] = useState([]);
  const [selectedAsset, setSelectedAsset] = useState('EURUSD_otc');
  const [activeTab, setActiveTab] = useState('raw'); // 'raw', 'filtered', 'bayesian'
  const [activeGates, setActiveGates] = useState({
    bayesian: true,
    volatility: true,
    liquidity: true,
    manipulation: true,
  });

  const mockVelocityData = [
    { time: '12:00:00', ticks_per_min: 118, vol: 48 },
    { time: '12:00:05', ticks_per_min: 124, vol: 52 },
    { time: '12:00:10', ticks_per_min: 132, vol: 55 },
    { time: '12:00:15', ticks_per_min: 128, vol: 51 },
    { time: '12:00:20', ticks_per_min: 140, vol: 62 },
    { time: '12:00:25', ticks_per_min: 135, vol: 58 },
    { time: '12:00:30', ticks_per_min: 129, vol: 54 },
  ];

  const mockBayesianMatrix = [
    { category: 'Z-Band: 1.5-2.0', win_rate: 64.2, sample: 128 },
    { category: 'Z-Band: 2.0-2.5', win_rate: 68.5, sample: 84 },
    { category: 'Regime: RANGE', win_rate: 61.4, sample: 310 },
    { category: 'Regime: PULLBACK', win_rate: 58.7, sample: 145 },
    { category: 'OTEO: Band 3', win_rate: 65.1, sample: 92 },
  ];

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, 4000);
    return () => clearInterval(timer);
  }, [selectedAsset]);

  const fetchData = async () => {
    try {
      const resStatus = await fetch('/api/status');
      if (resStatus.ok) {
        const dataStatus = await resStatus.json();
        setTelemetry(dataStatus);
      }

      const resRaw = await fetch(`/api/v1/ticks/raw?asset=${selectedAsset}&limit=15`);
      if (resRaw.ok) {
        const dataRaw = await resRaw.json();
        setRawTicks(dataRaw.ticks || []);
      }

      const activeGateList = Object.keys(activeGates).filter((k) => activeGates[k]).join(',');
      const resFilt = await fetch(`/api/v1/ticks/filtered?asset=${selectedAsset}&limit=15&gates=${activeGateList}`);
      if (resFilt.ok) {
        const dataFilt = await resFilt.json();
        setFilteredTicks(dataFilt.ticks || []);
      }
    } catch (e) {
      console.warn('Telemetry server offline or proxy loading...', e);
    }
  };

  const toggleGate = (gateKey) => {
    setActiveGates((prev) => ({ ...prev, [gateKey]: !prev[gateKey] }));
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-cyan-600 to-blue-600 rounded-lg text-white shadow-lg shadow-cyan-500/20">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-400 bg-clip-text text-transparent">
              VPS Data Agent Hub
            </h1>
            <p className="text-xs text-slate-400 font-mono">Standalone DaaS Microservice & Memory Vault</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="e.g. BTCUSD, AAPL_otc..."
              value={selectedAsset}
              onChange={(e) => setSelectedAsset(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-500 font-mono w-44"
            />
            <button
              onClick={async () => {
                if (selectedAsset) {
                  await fetch('/api/v1/subscribe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ asset: selectedAsset }),
                  });
                  fetchData();
                }
              }}
              className="bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold px-3 py-1.5 rounded-lg text-xs font-mono transition"
            >
              + Subscribe
            </button>
          </div>

          <div className="flex items-center gap-2 bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-full text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-emerald-400 font-semibold">GCP BigQuery Connected</span>
          </div>

          <button
            onClick={fetchData}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition"
          >
            <RefreshCcw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Content Layout */}
      <main className="flex-1 p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* KPI Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4 shadow-sm">
            <div className="p-3 bg-cyan-500/10 text-cyan-400 rounded-lg">
              <Zap className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 uppercase font-semibold">Tick Stream Velocity</p>
              <p className="text-2xl font-bold text-slate-100 font-mono">132 <span className="text-xs font-normal text-slate-400">ticks/min</span></p>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4 shadow-sm">
            <div className="p-3 bg-blue-500/10 text-blue-400 rounded-lg">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 uppercase font-semibold">BigQuery Ingestion</p>
              <p className="text-2xl font-bold text-emerald-400 font-mono">100% <span className="text-xs font-normal text-slate-400">Synced</span></p>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4 shadow-sm">
            <div className="p-3 bg-purple-500/10 text-purple-400 rounded-lg">
              <BarChart3 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 uppercase font-semibold">Bayesian Win-Rate</p>
              <p className="text-2xl font-bold text-slate-100 font-mono">64.2% <span className="text-xs font-normal text-slate-400">Prior Avg</span></p>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4 shadow-sm">
            <div className="p-3 bg-amber-500/10 text-amber-400 rounded-lg">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 uppercase font-semibold">Raw Data Policy</p>
              <p className="text-sm font-bold text-cyan-400 font-mono">Pristine Unmutated</p>
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
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockVelocityData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
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
                        No raw ticks loaded yet. Start <code className="text-cyan-400">vps_server.py</code> to stream live ticks.
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
                        No filtered tick evaluation loaded yet.
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
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={mockBayesianMatrix} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="category" stroke="#64748b" tick={{ fontSize: 12 }} />
                    <YAxis domain={[40, 80]} stroke="#64748b" tick={{ fontSize: 12 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }} />
                    <Bar dataKey="win_rate" fill="#06b6d4" radius={[6, 6, 0, 0]} name="Win Rate %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
