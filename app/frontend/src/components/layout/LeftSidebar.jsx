/**
 * LeftSidebar — collapsible navigation + asset list.
 * Collapse state persisted via useLayoutStore.
 */
import { useMemo, useState } from 'react';
import { ChevronDown, ChevronLeft, ChevronRight, BarChart2, Star, Search, Filter } from 'lucide-react';
import { useLayoutStore } from '../../stores/useLayoutStore.js';
import { useAssetStore } from '../../stores/useAssetStore.js';

const DEFAULT_PAYOUT_THRESHOLD = 92;
const QUICK_PAYOUT_PRESETS = [
  { value: DEFAULT_PAYOUT_THRESHOLD, label: '92%+' },
  { value: 90, label: '90%+' },
  { value: 85, label: '85%+' },
  { value: 80, label: '80%+' },
  { value: 75, label: '75%+' },
  { value: 60, label: '60%+' },
];
const ASSET_TYPE_OPTIONS = [
  { value: 'all', label: 'ALL' },
  { value: 'currencies', label: 'CURRENCIES' },
  { value: 'crypto', label: 'CRYPTO' },
  { value: 'stocks', label: 'STOCKS' },
  { value: 'indices', label: 'INDICES' },
];
const CRYPTO_SYMBOL_PREFIXES = ['BTC', 'ETH', 'LTC', 'XRP', 'BCH', 'DOGE', 'DOT', 'ADA', 'SOL', 'AVAX', 'LINK', 'UNI', 'XLM', 'TRX', 'ETC', 'MATIC', 'TON', 'NEAR', 'ATOM'];
const INDEX_PATTERN = /\b(INDEX|INDICE|S&P|SP500|US500|US100|NASDAQ|DOW|DJI|DJ30|FTSE|UK100|DAX|GER40|CAC|FRA40|NIKKEI|JPN225|AEX|EUSTX50|HANG SENG|HSI|IBEX|AUS200)\b/i;
const CRYPTO_NAME_PATTERN = /\b(BITCOIN|ETHEREUM|LITECOIN|RIPPLE|DOGECOIN|CARDANO|SOLANA|POLKADOT|CHAINLINK|AVALANCHE|SHIBA|TRON|STELLAR|TONCOIN|NEAR)\b/i;

export default function LeftSidebar() {
  const { sidebarOpen, setSidebarOpen } = useLayoutStore();
  const {
    selectedAsset,
    availableAssets,
    assetPayouts,
    assetDetails,
    setSelectedAsset,
    starredAssets,
    toggleStarredAsset,
  } = useAssetStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [payoutThreshold, setPayoutThreshold] = useState(DEFAULT_PAYOUT_THRESHOLD);
  const [otcOnly, setOtcOnly] = useState(false);
  const [assetTypeFilter, setAssetTypeFilter] = useState('all');
  const [filtersOpen, setFiltersOpen] = useState(true);

  const searchFilteredAssets = useMemo(() => {
    if (!searchQuery.trim()) return availableAssets;
    const query = searchQuery.toLowerCase().trim();
    return availableAssets.filter((asset) =>
      asset.toLowerCase().includes(query)
    );
  }, [availableAssets, searchQuery]);

  const filteredAssets = useMemo(() => {
    const minimumPayout = payoutThreshold / 100;

    return [...searchFilteredAssets]
      .filter((asset) => {
        const detail = assetDetails[asset];
        const payout = Number(assetPayouts[asset] ?? detail?.payout ?? 0);
        if (payout < minimumPayout) return false;
        if (otcOnly && !asset.toLowerCase().includes('_otc')) return false;
        if (assetTypeFilter === 'all') return true;
        return resolveAssetClass(asset, detail) === assetTypeFilter;
      })
      .sort((leftAsset, rightAsset) => {
        const leftPayout = Number(assetPayouts[leftAsset] ?? assetDetails[leftAsset]?.payout ?? 0);
        const rightPayout = Number(assetPayouts[rightAsset] ?? assetDetails[rightAsset]?.payout ?? 0);
        if (rightPayout !== leftPayout) {
          return rightPayout - leftPayout;
        }
        return leftAsset.localeCompare(rightAsset);
      });
  }, [assetDetails, assetPayouts, assetTypeFilter, otcOnly, payoutThreshold, searchFilteredAssets]);

  const starredList = useMemo(() =>
    filteredAssets.filter(asset => starredAssets.includes(asset)),
    [filteredAssets, starredAssets]
  );

  const unstarredList = useMemo(() =>
    filteredAssets.filter(asset => !starredAssets.includes(asset)),
    [filteredAssets, starredAssets]
  );

  const hasActiveSearch = searchQuery.trim().length > 0;
  const hasCustomFilter = otcOnly || assetTypeFilter !== 'all' || payoutThreshold !== DEFAULT_PAYOUT_THRESHOLD;

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

      {sidebarOpen && (
        <div className="flex flex-col flex-1 overflow-hidden">
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
            <div className="mt-2 rounded-lg border border-white/5 bg-white/[0.02]">
              <button
                type="button"
                onClick={() => setFiltersOpen((value) => !value)}
                className="flex w-full items-center justify-between gap-2 p-2 text-left"
                aria-expanded={filtersOpen}
                aria-label="Toggle asset filters"
              >
                <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">
                  <Filter size={11} />
                  Filters
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full border border-[#f5df19]/20 bg-[#f5df19]/10 px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.18em] text-[#f5df19]">
                    {payoutThreshold}%+
                  </span>
                  <ChevronDown size={12} className={`text-gray-500 transition-transform ${filtersOpen ? 'rotate-180' : 'rotate-0'}`} />
                </div>
              </button>

              {filtersOpen && (
                <div className="border-t border-white/5 px-2 pb-2">
                  <div className="mt-2 flex flex-wrap gap-1">
                    {QUICK_PAYOUT_PRESETS.map((preset) => (
                      <FilterChip
                        key={preset.value}
                        label={preset.label}
                        active={payoutThreshold === preset.value}
                        onClick={() => setPayoutThreshold(preset.value)}
                      />
                    ))}
                  </div>

                  <div className="mt-2 flex items-center justify-between rounded-md border border-white/5 bg-[#0f1419] px-2 py-1.5">
                    <div className="min-w-0">
                      <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-gray-500">OTC Only</p>
                      <p className="text-[10px] text-gray-600">{otcOnly ? 'Showing OTC assets only' : 'Showing all live assets'}</p>
                    </div>
                    <ToggleSwitch checked={otcOnly} onChange={() => setOtcOnly((value) => !value)} />
                  </div>

                  <div className="mt-2 flex flex-wrap gap-1">
                    {ASSET_TYPE_OPTIONS.map((option) => (
                      <FilterChip
                        key={option.value}
                        label={option.label}
                        active={assetTypeFilter === option.value}
                        onClick={() => setAssetTypeFilter(option.value)}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar">
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

            <div className="flex flex-col">
              <div className="flex items-center gap-1.5 px-3 py-2 border-b border-white/5">
                <BarChart2 size={12} className="text-gray-500" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">
                  {hasActiveSearch ? `Search Results (${unstarredList.length})` : `All Assets (${unstarredList.length})`}
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
              {(availableAssets.length > 0 || hasActiveSearch || hasCustomFilter) && filteredAssets.length === 0 && (
                <div className="px-3 py-8 text-center">
                  <p className="text-[10px] text-gray-600 italic">
                    {hasActiveSearch || hasCustomFilter
                      ? 'No assets match the current filters.'
                      : 'No assets available.'}
                  </p>
                </div>
              )}
              {availableAssets.length === 0 && !hasActiveSearch && (
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

function FilterChip({ label, active, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        rounded-full border px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.18em] transition-colors
        ${active
          ? 'border-[#f5df19]/30 bg-[#f5df19]/12 text-[#f5df19]'
          : 'border-white/5 bg-[#0f1419] text-gray-500 hover:border-white/10 hover:text-[#e3e6e7]'}
      `}
    >
      {label}
    </button>
  );
}

function ToggleSwitch({ checked, onChange }) {
  return (
    <button
      type="button"
      onClick={onChange}
      className={`relative inline-flex h-5 w-9 items-center rounded-full border transition-colors ${checked ? 'border-[#f5df19]/40 bg-[#f5df19]' : 'border-white/10 bg-white/10'}`}
      aria-pressed={checked}
      aria-label="Toggle OTC only assets"
    >
      <span className={`inline-block h-4 w-4 rounded-full bg-[#0f1419] transition-transform ${checked ? 'translate-x-4' : 'translate-x-0.5'}`} />
    </button>
  );
}

function resolveAssetClass(asset, detail) {
  const rawId = String(detail?.raw_id ?? asset).trim();
  const name = String(detail?.name ?? rawId).trim();
  const category = String(detail?.metadata?.category ?? '').trim().toLowerCase();
  const assetType = String(detail?.asset_type ?? '').trim().toLowerCase();
  const symbol = rawId.replace(/_otc$/i, '').replace(/^#/, '').toUpperCase();

  if (category.includes('crypto')) return 'crypto';
  if (category.includes('stock')) return 'stocks';
  if (category.includes('index') || category.includes('indice')) return 'indices';
  if (assetType === 'crypto') return 'crypto';
  if (assetType === 'stock') return 'stocks';
  if (assetType === 'forex') return 'currencies';
  if (rawId.startsWith('#')) return 'stocks';
  if (INDEX_PATTERN.test(`${symbol} ${name}`)) return 'indices';
  if (CRYPTO_SYMBOL_PREFIXES.some((prefix) => symbol.startsWith(prefix))) return 'crypto';
  if (CRYPTO_NAME_PATTERN.test(name.toUpperCase())) return 'crypto';
  return 'currencies';
}
