import React, { useState, useEffect, useRef } from 'react';
import { Plus, X } from 'lucide-react';
import MiniSparkline from './MiniSparkline';
import { normalizeAsset } from '../utils/assetUtils';

const MultiChartView = ({ socket, allAssets, onFocusAsset }) => {
  const [watchedAssets, setWatchedAssets] = useState([]);
  const [multiData, setMultiData] = useState({});
  const [isAdding, setIsAdding] = useState(false);
  const [gridSize, setGridSize] = useState('2x2'); // 2x2, 2x3, 3x3

  const maxAssets = gridSize === '2x2' ? 4 : gridSize === '2x3' ? 6 : 9;

  // Listen to multi_market_data or handle individual emits
  // We need to update socket listeners to capture data for watched assets
  useEffect(() => {
    if (!socket) return;

    const pendingUpdates = useRef({});
    const flushInterval = useRef(null);

    // We assume backend will emit 'market_data' with asset included
    const handleMarketData = (data) => {
      const asset = normalizeAsset(data.asset);
      if (!watchedAssets.includes(asset)) return;

      if (!pendingUpdates.current[asset]) {
        pendingUpdates.current[asset] = {};
      }
      const pending = pendingUpdates.current[asset];

      if (data.price) {
        pending.newPrice = data.price;
      }
      if (data.oteo_score !== undefined) pending.oteoScore = data.oteo_score;
      if (data.action || data.recommended) pending.action = data.action || data.recommended;
      if (data.confidence) pending.confidence = data.confidence;
      if (data.manipulation) pending.manipulation = data.manipulation;
    };

    const handleWarmupStatus = (data) => {
        const asset = normalizeAsset(data.asset);
        if (!watchedAssets.includes(asset)) return;

        if (!pendingUpdates.current[asset]) {
          pendingUpdates.current[asset] = {};
        }
        pendingUpdates.current[asset].warmup = { ready: data.ready, ticks: data.ticks_received };
    };

    socket.on('market_data', handleMarketData);
    socket.on('warmup_status', handleWarmupStatus);

    // Throttle rendering by flushing pending updates every 100ms
    flushInterval.current = setInterval(() => {
      if (Object.keys(pendingUpdates.current).length === 0) return;

      setMultiData(prev => {
        const nextState = { ...prev };
        let changed = false;

        for (const [asset, updates] of Object.entries(pendingUpdates.current)) {
          const assetData = nextState[asset] || { prices: [], oteoScore: 50, action: 'CALL', confidence: 'LOW', manipulation: {}, warmup: { ready: false, ticks: 0 } };
          
          const newPrices = updates.newPrice 
            ? [...assetData.prices.slice(-99), updates.newPrice] 
            : assetData.prices;

          nextState[asset] = {
            ...assetData,
            prices: newPrices,
            oteoScore: updates.oteoScore !== undefined ? updates.oteoScore : assetData.oteoScore,
            action: updates.action || assetData.action,
            confidence: updates.confidence || assetData.confidence,
            manipulation: updates.manipulation || assetData.manipulation,
            warmup: updates.warmup || assetData.warmup
          };
          changed = true;
        }

        pendingUpdates.current = {}; // Reset after applying
        return changed ? nextState : prev;
      });
    }, 100);

    return () => {
      socket.off('market_data', handleMarketData);
      socket.off('warmup_status', handleWarmupStatus);
      if (flushInterval.current) clearInterval(flushInterval.current);
    };
  }, [socket, watchedAssets]);

  // When watched assets change, emit watch_assets
  useEffect(() => {
    if (socket && watchedAssets.length > 0) {
      socket.emit('watch_assets', { assets: watchedAssets });
    }
  }, [socket, watchedAssets]);

  const addAsset = (asset) => {
    if (watchedAssets.length >= maxAssets) return;
    const normalized = normalizeAsset(asset.id);
    if (!watchedAssets.includes(normalized)) {
      setWatchedAssets(prev => [...prev, normalized]);
    }
    setIsAdding(false);
  };

  const removeAsset = (asset, e) => {
    e.stopPropagation();
    setWatchedAssets(prev => prev.filter(a => a !== asset));
    setMultiData(prev => {
        const newData = { ...prev };
        delete newData[asset];
        return newData;
    });
  };

  const gridClass = {
    '2x2': 'grid-cols-2 grid-rows-2',
    '2x3': 'grid-cols-3 grid-rows-2',
    '3x3': 'grid-cols-3 grid-rows-3'
  }[gridSize];

  return (
    <div className="w-full h-full flex flex-col p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-sm font-bold text-white uppercase tracking-widest">Multi-Chart View</h2>
        <div className="flex gap-2">
          <select 
            value={gridSize}
            onChange={e => setGridSize(e.target.value)}
            className="bg-slate-800 text-white text-xs p-1 rounded border border-slate-700"
          >
            <option value="2x2">2x2 (4 Assets)</option>
            <option value="2x3">2x3 (6 Assets)</option>
            <option value="3x3">3x3 (9 Assets)</option>
          </select>
        </div>
      </div>

      <div className={`grid ${gridClass} gap-4 flex-1`}>
        {watchedAssets.map(asset => (
          <div key={asset} className="relative group">
            <MiniSparkline
              asset={asset}
              prices={multiData[asset]?.prices}
              oteoScore={multiData[asset]?.oteoScore}
              action={multiData[asset]?.action}
              confidence={multiData[asset]?.confidence}
              manipulation={multiData[asset]?.manipulation}
              warmup={multiData[asset]?.warmup}
              onClick={() => onFocusAsset(asset)}
            />
            <button 
              onClick={(e) => removeAsset(asset, e)}
              className="absolute -top-2 -right-2 bg-slate-800 border border-slate-600 rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity z-20 hover:bg-red-500/20"
            >
              <X className="w-3 h-3 text-slate-400 hover:text-red-500" />
            </button>
          </div>
        ))}

        {watchedAssets.length < maxAssets && (
          <div className="relative">
            {isAdding ? (
              <div className="w-full h-[120px] bg-slate-800/50 border border-slate-700 border-dashed rounded-lg p-2 overflow-y-auto">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-bold text-slate-400">Select Asset</span>
                  <X className="w-3 h-3 cursor-pointer text-slate-500 hover:text-white" onClick={() => setIsAdding(false)} />
                </div>
                <div className="flex flex-col gap-1">
                  {allAssets.filter(a => !watchedAssets.includes(normalizeAsset(a.id))).map(a => (
                    <div 
                      key={a.id} 
                      className="text-[10px] p-1 hover:bg-slate-700 cursor-pointer rounded"
                      onClick={() => addAsset(a)}
                    >
                      {a.name}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <button 
                onClick={() => setIsAdding(true)}
                className="w-full h-[120px] bg-slate-800/30 border border-slate-700 border-dashed rounded-lg flex flex-col items-center justify-center text-slate-500 hover:text-cyan-400 hover:border-cyan-400/50 hover:bg-cyan-400/5 transition-all"
              >
                <Plus className="w-6 h-6 mb-1" />
                <span className="text-xs font-bold uppercase tracking-wider">Add Asset</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MultiChartView;
