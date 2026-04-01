/**
 * LeftSidebar — collapsible navigation + asset list.
 * Collapse state persisted via useLayoutStore.
 */
import React, { useState, useMemo } from 'react';
import { ChevronLeft, ChevronRight, BarChart2, TrendingUp, ShieldAlert, Settings, BookOpen, Star, Search, Filter } from 'lucide-react';
import { useLayoutStore } from '../../stores/useLayoutStore.js';
import { useAssetStore } from '../../stores/useAssetStore.js';

const NAV_ITEMS = [
  { id: 'trading',  label: 'Trading',      icon: TrendingUp },
  { id: 'risk',     label: 'Risk Manager', icon: ShieldAlert },
  { id: 'journal',  label: 'Journal',      icon: BookOpen },
  { id: 'settings', label: 'Settings',     icon: Settings },
];

export default function LeftSidebar() {
  const { sidebarOpen, setSidebarOpen, activeView, setActiveView } = useLayoutStore();
  const { 
    selectedAsset, 
    availableAssets, 
    assetPayouts, 
    setSelectedAsset,
    starredAssets,
    toggleStarredAsset 
  } = useAssetStore();

  const [searchQuery, setSearchQuery] = useState('');

  // Filter assets based on search query
  const filteredAssets = useMemo(() => {
    if (!searchQuery.trim()) return availableAssets;
    const query = searchQuery.toLowerCase().trim();
    return availableAssets.filter(asset => 
      asset.toLowerCase().includes(query)
    );
  }, [availableAssets, searchQuery]);

  // Separate starred and unstarred from the filtered list
  const starredList = useMemo(() => 
    filteredAssets.filter(asset => starredAssets.includes(asset)),
    [filteredAssets, starredAssets]
  );

  const unstarredList = useMemo(() => 
    filteredAssets.filter(asset => !starredAssets.includes(asset)),
    [filteredAssets, starredAssets]
  );

  return (
    <aside className={`
      flex flex-col shrink-0
      border-r border-white/5
      bg-[#0f1419]
      transition-all duration-200
      ${sidebarOpen ? 'w-[220px]' : 'w-12'}
    `}>
      {/* Toggle button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="flex items-center justify-center h-10 w-full border-b border-white/5 text-gray-500 hover:text-gray-300 hover:bg-white/5 transition-colors shrink-0"
        title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
      >
        {sidebarOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
      </button>

      {/* Navigation */}
      <nav className="flex flex-col gap-0.5 p-1.5 border-b border-white/5">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveView(id)}
            title={!sidebarOpen ? label : undefined}
            className={`
              flex items-center gap-2.5 px-2 py-1.5 rounded-md text-xs font-medium transition-colors
              ${activeView === id
                ? 'bg-[#f5df19]/15 text-[#f5df19] shadow-[inset_0_0_0_1px_rgba(245,223,25,0.18)]'
                : 'text-gray-500 hover:bg-white/5 hover:text-[#e3e6e7]'}
            `}
          >
            <Icon size={15} className="shrink-0" />
            {sidebarOpen && <span className="truncate">{label}</span>}
          </button>
        ))}
      </nav>

      {/* Asset list — only shown when expanded */}
      {sidebarOpen && (
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Asset Search */}
          <div className="px-2 py-2 border-b border-white/5">
            <div className="relative group">
              <Search 
                size={12} 
                className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-[#f5df19] transition-colors" 
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search Assets..."
                className="w-full bg-white/5 border border-white/10 rounded-md py-1.5 pl-7 pr-2 text-[11px] text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-[#f5df19]/30 focus:bg-white/10 transition-all"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {/* Quick Select / Starred Assets */}
            {starredList.length > 0 && (
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5 px-3 py-2 border-b border-white/5 bg-white/[0.02]">
                  <Star size={10} className="text-[#f5df19] fill-[#f5df19]" />
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-[#f5df19]">Quick Select</span>
                </div>
                <ul className="py-1">
                  {starredList.map((asset) => (
                    <AssetRow 
                      key={asset}
                      asset={asset}
                      isSelected={selectedAsset === asset}
                      payout={assetPayouts?.[asset]}
                      isStarred={true}
                      onSelect={() => setSelectedAsset(asset)}
                      onToggleStar={() => toggleStarredAsset(asset)}
                    />
                  ))}
                </ul>
              </div>
            )}

            {/* All Assets */}
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5 px-3 py-2 border-b border-white/5">
                <BarChart2 size={12} className="text-gray-500" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">
                  {searchQuery ? 'Search Results' : `All Assets (${unstarredList.length})`}
                </span>
              </div>
              <ul className="py-1">
                {unstarredList.map((asset) => (
                  <AssetRow 
                    key={asset}
                    asset={asset}
                    isSelected={selectedAsset === asset}
                    payout={assetPayouts?.[asset]}
                    isStarred={false}
                    onSelect={() => setSelectedAsset(asset)}
                    onToggleStar={() => toggleStarredAsset(asset)}
                  />
                ))}
              </ul>
              {filteredAssets.length === 0 && searchQuery && (
                <div className="px-3 py-8 text-center">
                  <p className="text-[10px] text-gray-600 italic">No assets matching &quot;{searchQuery}&quot;</p>
                </div>
              )}
              {availableAssets.length === 0 && !searchQuery && (
                <div className="px-3 py-10 text-center flex flex-col items-center gap-2">
                  <BarChart2 size={20} className="text-gray-700" />
                  <p className="text-[10px] text-gray-600 leading-relaxed">
                    Connect your SSID to<br />load live assets &amp; payouts
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}

function AssetRow({ asset, isSelected, payout, isStarred, onSelect, onToggleStar }) {
  const payoutLabel = payout != null ? `${Math.round(payout * 100)}%` : null;
  const displayName = asset.replace('_otc', '').toUpperCase();
  const isOTC = asset.toLowerCase().includes('_otc');

  return (
    <li className="group/row">
      <div
        className={`
          flex items-center justify-between px-3 py-1 text-xs transition-colors
          ${isSelected
            ? 'bg-[#f5df19]/15 text-[#f5df19]'
            : 'text-gray-400 hover:bg-white/5'}
        `}
      >
        <button
          onClick={onSelect}
          className="flex-1 flex items-center gap-1.5 text-left py-1 overflow-hidden"
        >
          <span className={`truncate ${isSelected ? 'font-bold' : ''}`}>
            {displayName}
            {isOTC && <span className="ml-1 text-[8px] text-gray-500 font-normal">OTC</span>}
          </span>
          {payoutLabel && (
            <span
              className={`
                text-[9px] font-bold px-1 rounded
                ${isSelected
                  ? 'text-[#f5df19]'
                  : 'text-emerald-500'}
              `}
            >
              {payoutLabel}
            </span>
          )}
        </button>
        
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleStar();
          }}
          className={`
            p-1 rounded hover:bg-white/10 transition-all
            ${isStarred ? 'opacity-100' : 'opacity-0 group-hover/row:opacity-100'}
          `}
        >
          <Star 
            size={12} 
            className={`${isStarred ? 'text-[#f5df19] fill-[#f5df19]' : 'text-gray-600'}`} 
          />
        </button>
      </div>
    </li>
  );
}
