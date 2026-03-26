import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config';

const STREAM_URL = import.meta.env.VITE_STREAM_URL || "http://localhost:3001";

const SettingsView = () => {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await axios.get(`${STREAM_URL}/api/settings/global`);
      setSettings(res.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = async (key, value) => {
    try {
      await axios.put(`${STREAM_URL}/api/settings/global/${key}`, { value });
      // Optimistic update
      setSettings(prev => {
        const next = { ...prev };
        const keys = key.split('.');
        let target = next;
        for (let i = 0; i < keys.length - 1; i++) {
          target = target[keys[i]];
        }
        target[keys[keys.length - 1]] = value;
        return next;
      });
    } catch (err) {
      console.error(err);
      setError("Failed to update setting");
    }
  };

  if (loading) return <div className="p-4 text-white">Loading settings...</div>;
  if (error) return <div className="p-4 text-red-400">Error: {error}</div>;
  if (!settings) return null;

  return (
    <div className="p-6 max-w-4xl mx-auto text-slate-200 h-full overflow-y-auto">
      <h2 className="text-xl font-bold text-white mb-6 uppercase tracking-widest border-b border-slate-700 pb-2">Platform Settings</h2>
      
      <div className="space-y-8">
        {/* General */}
        <section className="bg-slate-800 p-4 rounded-xl border border-slate-700">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">General</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col">
              <label className="text-xs text-slate-500 mb-1">Theme</label>
              <select 
                className="bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white"
                value={settings.theme}
                onChange={e => updateSetting('theme', e.target.value)}
              >
                <option value="dark">Dark</option>
                <option value="light">Light</option>
              </select>
            </div>
            <div className="flex flex-col">
              <label className="text-xs text-slate-500 mb-1">Data Retention (Days)</label>
              <input 
                type="number" 
                className="bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white"
                value={settings.data_retention_days}
                onChange={e => updateSetting('data_retention_days', parseInt(e.target.value))}
              />
            </div>
          </div>
        </section>

        {/* OTEO */}
        <section className="bg-slate-800 p-4 rounded-xl border border-slate-700">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">OTEO Engine</h3>
          <div className="grid grid-cols-2 gap-4">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input 
                type="checkbox" 
                checked={settings.oteo.multi_timeframe}
                onChange={e => updateSetting('oteo.multi_timeframe', e.target.checked)}
                className="rounded bg-slate-900 border-slate-700"
              />
              Multi-Timeframe Confirmation
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input 
                type="checkbox" 
                checked={settings.oteo.manipulation_suppression}
                onChange={e => updateSetting('oteo.manipulation_suppression', e.target.checked)}
                className="rounded bg-slate-900 border-slate-700"
              />
              Manipulation Suppression
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input 
                type="checkbox" 
                checked={settings.oteo.volatility_adaptive}
                onChange={e => updateSetting('oteo.volatility_adaptive', e.target.checked)}
                className="rounded bg-slate-900 border-slate-700"
              />
              Volatility Adaptive
            </label>
            <div className="flex flex-col">
              <label className="text-xs text-slate-500 mb-1">Cooldown Ticks</label>
              <input 
                type="number" 
                className="bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white"
                value={settings.oteo.cooldown_ticks}
                onChange={e => updateSetting('oteo.cooldown_ticks', parseInt(e.target.value))}
              />
            </div>
          </div>
        </section>

        {/* Ghost Trading */}
        <section className="bg-slate-800 p-4 rounded-xl border border-slate-700">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">Ghost Trading</h3>
          <div className="grid grid-cols-2 gap-4">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input 
                type="checkbox" 
                checked={settings.ghost_trading.enabled}
                onChange={e => updateSetting('ghost_trading.enabled', e.target.checked)}
                className="rounded bg-slate-900 border-slate-700 text-neon"
              />
              Enable Ghost Trading
            </label>
            <div className="flex flex-col">
              <label className="text-xs text-slate-500 mb-1">Default Ghost Amount ($)</label>
              <input 
                type="number" 
                className="bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white"
                value={settings.ghost_trading.default_amount}
                onChange={e => updateSetting('ghost_trading.default_amount', parseFloat(e.target.value))}
              />
            </div>
          </div>
        </section>

        {/* Trading Controls */}
        <section className="bg-slate-800 p-4 rounded-xl border border-slate-700">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">Trading Controls</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col">
              <label className="text-xs text-slate-500 mb-1">Max Concurrent Trades</label>
              <input
                type="number" min="1" max="10"
                className="bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white"
                value={settings.trading?.max_concurrent_trades || 3}
                onChange={e => updateSetting('trading.max_concurrent_trades', parseInt(e.target.value))}
              />
            </div>
            <div className="flex flex-col">
              <label className="text-xs text-slate-500 mb-1">Default Amount ($)</label>
              <input
                type="number"
                className="bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white"
                value={settings.trading?.default_amount || 10}
                onChange={e => updateSetting('trading.default_amount', parseFloat(e.target.value))}
              />
            </div>
            <div className="flex flex-col">
              <label className="text-xs text-slate-500 mb-1">Cooldown (ms)</label>
              <input
                type="number"
                className="bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white"
                value={settings.trading?.cooldown_between_trades_ms || 1000}
                onChange={e => updateSetting('trading.cooldown_between_trades_ms', parseInt(e.target.value))}
              />
            </div>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={settings.trading?.allow_same_asset_trades || false}
                onChange={e => updateSetting('trading.allow_same_asset_trades', e.target.checked)}
                className="rounded bg-slate-900 border-slate-700"
              />
              Allow Same-Asset Trades
            </label>
          </div>
        </section>
      </div>
    </div>
  );
};

export default SettingsView;
