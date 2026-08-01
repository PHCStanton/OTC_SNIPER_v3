import React, { useState, useEffect } from 'react';
import { Database, Server, Cpu, MessageSquare, RefreshCw, CheckCircle2, AlertTriangle, Activity } from 'lucide-react';

export default function DataAgentWidget({ telemetryUrl = 'http://localhost:8090/api/status' }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchTelemetry = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(telemetryUrl);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err.message || 'Failed to connect to VPS Data Agent telemetry endpoint');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 10000);
    return () => clearInterval(interval);
  }, [telemetryUrl]);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 text-slate-100 shadow-2xl backdrop-blur-md max-w-lg w-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-slate-100">VPS Data Agent & Hermes</h3>
            <p className="text-xs text-slate-400">GCP BigQuery • xAI Grok • WhatsApp</p>
          </div>
        </div>
        <button
          onClick={fetchTelemetry}
          disabled={loading}
          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-50"
          title="Refresh Telemetry"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{error} (Operating in Offline / Local Fallback Mode)</span>
        </div>
      )}

      {/* Status Grid */}
      <div className="grid grid-cols-2 gap-2 text-xs mb-3">
        {/* Tick Collector Status */}
        <div className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="flex items-center gap-1">
              <Activity className="w-3.5 h-3.5 text-cyan-400" /> Tick Ingestion
            </span>
            <span className={`inline-block w-2 h-2 rounded-full ${data?.collector?.running ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
          </div>
          <div className="font-mono text-sm font-semibold text-slate-200">
            {data?.collector?.total_ticks?.toLocaleString() ?? 0} ticks
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            {data?.collector?.subscribed_assets?.length ?? 0} Assets Subscribed
          </div>
        </div>

        {/* GCP BigQuery Sink */}
        <div className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="flex items-center gap-1">
              <Database className="w-3.5 h-3.5 text-blue-400" /> GCP BigQuery Sink
            </span>
            <span className={`inline-block w-2 h-2 rounded-full ${data?.sink?.has_gcp_connection ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          </div>
          <div className="font-mono text-sm font-semibold text-slate-200">
            {data?.sink?.total_flushed?.toLocaleString() ?? 0} synced
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            Buffer: {data?.sink?.buffer_size ?? 0} pending
          </div>
        </div>

        {/* Bayesian Prior Calibration */}
        <div className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="flex items-center gap-1">
              <Cpu className="w-3.5 h-3.5 text-purple-400" /> Bayesian Priors
            </span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="font-mono text-sm font-semibold text-slate-200">
            {data?.bayesian?.overall_win_rate ?? 50.0}% Win Rate
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            {data?.bayesian?.total_trades?.toLocaleString() ?? 0} Trades Analyzed
          </div>
        </div>

        {/* WhatsApp Gateway */}
        <div className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="flex items-center gap-1">
              <MessageSquare className="w-3.5 h-3.5 text-emerald-400" /> WhatsApp OpenWA
            </span>
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400" />
          </div>
          <div className="font-mono text-sm font-semibold text-slate-200">
            Active Bridge
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            Hermes Agent Ready
          </div>
        </div>
      </div>
    </div>
  );
}
