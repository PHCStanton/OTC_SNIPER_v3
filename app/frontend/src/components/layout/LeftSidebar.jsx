/**
 * LeftSidebar — collapsible navigation + asset list.
 * Collapse state persisted via useLayoutStore.
 */
import { ChevronLeft, ChevronRight, BarChart2, TrendingUp, ShieldAlert, Settings, BookOpen } from 'lucide-react';
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
  const { selectedAsset, availableAssets, setSelectedAsset } = useAssetStore();

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
          <div className="flex items-center gap-1.5 px-3 py-2 border-b border-white/5">
            <BarChart2 size={12} className="text-[#f5df19]" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#f5df19]">OTC Assets</span>
          </div>
          <ul className="flex-1 overflow-y-auto py-1">
            {availableAssets.map((asset) => (
              <li key={asset}>
                <button
                  onClick={() => setSelectedAsset(asset)}
                  className={`
                    w-full text-left px-3 py-1.5 text-xs transition-colors
                    ${selectedAsset === asset
                      ? 'bg-[#f5df19]/15 text-[#f5df19] font-medium'
                      : 'text-gray-400 hover:bg-white/5 hover:text-[#e3e6e7]'}
                  `}
                >
                  {asset.replace('_otc', '')}
                  <span className="ml-1 text-[9px] text-gray-500">OTC</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}
