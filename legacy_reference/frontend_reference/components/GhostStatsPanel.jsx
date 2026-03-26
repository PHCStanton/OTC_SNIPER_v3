import React, { useState, useEffect } from 'react';
import axios from 'axios';

const GhostStatsPanel = () => {
  const [stats, setStats] = useState({ trades: 0, wins: 0, losses: 0, ties: 0, profit: 0 });
  const [activeTrades, setActiveTrades] = useState([]);
  const [isOpen, setIsOpen] = useState(false);

  const [isGhostEnabled, setIsGhostEnabled] = useState(false);

  useEffect(() => {
    const fetchGlobalSettings = async () => {
      try {
        const streamUrl = import.meta.env.VITE_STREAM_URL || "http://localhost:3001";
        const res = await axios.get(`${streamUrl}/api/settings/global`);
        setIsGhostEnabled(res.data?.ghost_trading?.enabled || false);
      } catch (err) {
        console.error("Failed to fetch global settings:", err);
      }
    };
    fetchGlobalSettings();
  }, []);

  const toggleGhostMode = async () => {
    try {
      const streamUrl = import.meta.env.VITE_STREAM_URL || "http://localhost:3001";
      const newVal = !isGhostEnabled;
      await axios.put(`${streamUrl}/api/settings/global/ghost_trading.enabled`, { value: newVal });
      setIsGhostEnabled(newVal);
    } catch (err) {
      console.error("Failed to toggle ghost mode:", err);
    }
  };

  useEffect(() => {
    if (!isOpen) return;

    const fetchStats = async () => {
      try {
        const streamUrl = import.meta.env.VITE_STREAM_URL || "http://localhost:3001";
        const statsRes = await axios.get(`${streamUrl}/api/ghost/stats`);
        setStats(statsRes.data);

        const activeRes = await axios.get(`${streamUrl}/api/ghost/active`);
        setActiveTrades(activeRes.data);
      } catch (err) {
        console.error("Failed to fetch ghost stats:", err);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, [isOpen]);

  if (!isOpen) {
    return (
      <div 
        className="fixed bottom-4 right-4 bg-slate-800 text-white p-2 rounded-full cursor-pointer shadow-lg hover:bg-slate-700 z-50 border border-slate-600"
        onClick={() => setIsOpen(true)}
      >
        <span className="text-xl">👻</span>
      </div>
    );
  }

  const winRate = stats.trades > 0 ? ((stats.wins / stats.trades) * 100).toFixed(1) : 0;

  return (
    <div className="fixed bottom-4 right-4 w-80 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl z-50 flex flex-col text-slate-200 overflow-hidden">
      <div className="flex justify-between items-center p-3 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <h3 className="font-bold flex items-center gap-2">
            <span>👻</span> Ghost Trading
          </h3>
          <button 
            onClick={toggleGhostMode}
            className={`ml-2 px-2 py-0.5 text-[10px] font-bold rounded ${isGhostEnabled ? 'bg-neon/20 text-neon' : 'bg-slate-700 text-slate-400'}`}
          >
            {isGhostEnabled ? 'ON' : 'OFF'}
          </button>
        </div>
        <button onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-white">✕</button>
      </div>
      
      <div className="p-4 flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-slate-800 p-3 rounded text-center">
            <div className="text-xs text-slate-400 uppercase">Win Rate</div>
            <div className={`text-xl font-bold ${winRate >= 60 ? 'text-green-400' : winRate >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
              {winRate}%
            </div>
          </div>
          <div className="bg-slate-800 p-3 rounded text-center">
            <div className="text-xs text-slate-400 uppercase">Profit</div>
            <div className={`text-xl font-bold ${stats.profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              ${stats.profit.toFixed(2)}
            </div>
          </div>
        </div>

        <div className="text-sm bg-slate-800 p-3 rounded flex justify-between">
          <span className="text-slate-400">Trades: {stats.trades}</span>
          <span className="text-green-400">W: {stats.wins}</span>
          <span className="text-red-400">L: {stats.losses}</span>
          <span className="text-slate-400">T: {stats.ties}</span>
        </div>

        <div>
          <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">Active Trades ({activeTrades.length})</h4>
          {activeTrades.length === 0 ? (
            <div className="text-sm text-slate-500 italic text-center p-2">No active ghost trades</div>
          ) : (
            <div className="max-h-40 overflow-y-auto pr-1 flex flex-col gap-2">
              {activeTrades.map(trade => (
                <div key={trade.id} className="text-xs bg-slate-800 p-2 rounded border border-slate-700 flex justify-between">
                  <div>
                    <span className={trade.direction === 'CALL' ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>
                      {trade.direction}
                    </span>
                    <span className="ml-2 font-mono">{trade.asset}</span>
                  </div>
                  <div className="text-slate-400">@ {trade.entry_price}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default GhostStatsPanel;
