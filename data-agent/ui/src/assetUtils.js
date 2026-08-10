/**
 * Asset catalog helpers & filter classification for Data Agent UI.
 * Mirrors patterns from LeftSidebar.jsx.
 */

export const DEFAULT_PAYOUT_THRESHOLD = 92;

export const QUICK_PAYOUT_PRESETS = [
  { value: 92, label: '92%+' },
  { value: 90, label: '90%+' },
  { value: 85, label: '85%+' },
  { value: 80, label: '80%+' },
  { value: 75, label: '75%+' },
  { value: 60, label: '60%+' },
];

export const ASSET_TYPE_OPTIONS = [
  { value: 'all', label: 'ALL' },
  { value: 'currencies', label: 'CURR' },
  { value: 'crypto', label: 'CRYP' },
  { value: 'stocks', label: 'STCK' },
  { value: 'indices', label: 'INDX' },
  { value: 'commodities', label: 'COMM' },
];

const CRYPTO_SYMBOL_PREFIXES = ['BTC', 'ETH', 'LTC', 'XRP', 'BCH', 'DOGE', 'DOT', 'ADA', 'SOL', 'AVAX', 'LINK', 'UNI', 'XLM', 'TRX', 'ETC', 'MATIC', 'TON', 'NEAR', 'ATOM'];
const INDEX_PATTERN = /\b(INDEX|INDICE|S&P|SP500|US500|US100|NASDAQ|DOW|DJI|DJ30|FTSE|UK100|DAX|GER40|CAC|FRA40|NIKKEI|JPN225|AEX|EUSTX50|HANG SENG|HSI|IBEX|AUS200)\b/i;
const CRYPTO_NAME_PATTERN = /\b(BITCOIN|ETHEREUM|LITECOIN|RIPPLE|DOGECOIN|CARDANO|SOLANA|POLKADOT|CHAINLINK|AVALANCHE|SHIBA|TRON|STELLAR|TONCOIN|NEAR)\b/i;
const COMMODITY_PATTERN = /\b(GOLD|SILVER|CRUDE|BRENT|OIL|PLATINUM|PALLADIUM|COPPER|NATGAS|GAS)\b/i;

/** Resolve asset class / category for filtering */
export function resolveAssetClass(item) {
  if (!item) return 'currencies';
  const symbol = String(item.symbol || '').trim();
  const name = String(item.name || symbol).trim();
  const category = String(item.category || '').trim().toLowerCase();
  const cleanSym = symbol.replace(/_otc$/i, '').replace(/^#/, '').toUpperCase();

  if (category.includes('crypto')) return 'crypto';
  if (category.includes('stock')) return 'stocks';
  if (category.includes('index') || category.includes('indice')) return 'indices';
  if (category.includes('commodit')) return 'commodities';
  if (symbol.startsWith('#')) return 'stocks';
  if (COMMODITY_PATTERN.test(cleanSym) || COMMODITY_PATTERN.test(name)) return 'commodities';
  if (INDEX_PATTERN.test(`${cleanSym} ${name}`)) return 'indices';
  if (CRYPTO_SYMBOL_PREFIXES.some((prefix) => cleanSym.startsWith(prefix))) return 'crypto';
  if (CRYPTO_NAME_PATTERN.test(name.toUpperCase())) return 'crypto';
  return 'currencies';
}

/** Format payout for display. Unknown/null → em dash percent. */
export function formatPayoutLabel(payout) {
  if (payout === null || payout === undefined || Number.isNaN(Number(payout))) {
    return '—%';
  }
  return `${Number(payout)}%`;
}

/** Format clean display name for header or rows */
export function formatDisplayName(symbol) {
  if (!symbol) return '';
  const clean = symbol.replace(/_otc$/i, '').replace(/^#/, '');
  if (clean.length === 6 && !clean.includes('/')) {
    return `${clean.slice(0, 3)}/${clean.slice(3)}`;
  }
  return clean;
}

/** Resolve selected catalog entry by symbol (exact match). */
export function resolveSelectedAsset(catalog, symbol) {
  if (!Array.isArray(catalog) || !symbol) return null;
  return catalog.find((item) => item.symbol === symbol) || null;
}

/** True when user input is non-empty after trim. */
export function canSubmitCustomAsset(input) {
  return typeof input === 'string' && input.trim().length > 0;
}

/**
 * Build a custom catalog entry after confirmed subscription.
 */
export function buildCustomCatalogEntry(ticker) {
  const symbol = String(ticker || '').trim();
  return {
    symbol,
    name: symbol,
    payout: null,
    category: 'Custom',
    live: true,
    velocity: null,
  };
}

/**
 * Filter catalog by search query, payout threshold, OTC toggle, and asset type.
 */
export function matchesFilters(item, { searchQuery = '', payoutThreshold = 0, otcOnly = false, assetTypeFilter = 'all' }) {
  if (!item) return false;

  // Search filter
  if (searchQuery.trim()) {
    const query = searchQuery.toLowerCase().trim();
    const matchesSym = item.symbol.toLowerCase().includes(query);
    const matchesName = (item.name || '').toLowerCase().includes(query);
    if (!matchesSym && !matchesName) return false;
  }

  // Payout threshold filter
  if (payoutThreshold > 0) {
    if (item.payout == null || Number(item.payout) < payoutThreshold) {
      return false;
    }
  }

  // OTC Only filter
  if (otcOnly && !item.symbol.toLowerCase().includes('_otc')) {
    return false;
  }

  // Asset type filter
  if (assetTypeFilter !== 'all') {
    const itemClass = resolveAssetClass(item);
    if (itemClass !== assetTypeFilter) {
      return false;
    }
  }

  return true;
}

/** Backward-compat helper */
export function matchesPayoutFilter(item, payoutFilter) {
  if (!item) return false;
  if (payoutFilter === '92%+') return item.payout != null && item.payout >= 92;
  if (payoutFilter === '90%+') return item.payout != null && item.payout >= 90;
  if (payoutFilter === '85%+') return item.payout != null && item.payout >= 85;
  if (payoutFilter === '80%+') return item.payout != null && item.payout >= 80;
  return true;
}

/** Comprehensive Pocket Option OTC Asset Catalog */
export const DEFAULT_FULL_ASSET_CATALOG = [
  // Currencies OTC (92% Payouts)
  { symbol: 'EURUSD_otc', name: 'EUR/USD OTC', payout: 92, category: 'Currencies', live: true, velocity: 132 },
  { symbol: 'GBPUSD_otc', name: 'GBP/USD OTC', payout: 92, category: 'Currencies', live: true, velocity: 128 },
  { symbol: 'USDJPY_otc', name: 'USD/JPY OTC', payout: 92, category: 'Currencies', live: true, velocity: 124 },
  { symbol: 'AUDCAD_otc', name: 'AUD/CAD OTC', payout: 92, category: 'Currencies', live: true, velocity: 130 },
  { symbol: 'USDCHF_otc', name: 'USD/CHF OTC', payout: 92, category: 'Currencies', live: true, velocity: 124 },
  { symbol: 'USDCAD_otc', name: 'USD/CAD OTC', payout: 92, category: 'Currencies', live: true, velocity: 126 },
  { symbol: 'EURGBP_otc', name: 'EUR/GBP OTC', payout: 92, category: 'Currencies', live: true, velocity: 120 },
  { symbol: 'EURJPY_otc', name: 'EUR/JPY OTC', payout: 92, category: 'Currencies', live: true, velocity: 135 },
  { symbol: 'GBPJPY_otc', name: 'GBP/JPY OTC', payout: 92, category: 'Currencies', live: true, velocity: 138 },
  { symbol: 'AUDJPY_otc', name: 'AUD/JPY OTC', payout: 92, category: 'Currencies', live: true, velocity: 122 },
  { symbol: 'AUDUSD_otc', name: 'AUD/USD OTC', payout: 92, category: 'Currencies', live: true, velocity: 125 },
  { symbol: 'NZDUSD_otc', name: 'NZD/USD OTC', payout: 92, category: 'Currencies', live: true, velocity: 119 },
  { symbol: 'CHFJPY_otc', name: 'CHF/JPY OTC', payout: 90, category: 'Currencies', live: true, velocity: 115 },
  { symbol: 'EURAUD_otc', name: 'EUR/AUD OTC', payout: 90, category: 'Currencies', live: true, velocity: 118 },
  { symbol: 'GBPAUD_otc', name: 'GBP/AUD OTC', payout: 90, category: 'Currencies', live: true, velocity: 121 },

  // Emerging Markets OTC
  { symbol: 'ZARUSD_otc', name: 'ZAR/USD OTC', payout: 92, category: 'Emerging', live: true, velocity: 122 },
  { symbol: 'NGNUSD_otc', name: 'NGN/USD OTC', payout: 92, category: 'Emerging', live: true, velocity: 125 },
  { symbol: 'USDARS_otc', name: 'USD/ARS OTC', payout: 92, category: 'Emerging', live: true, velocity: 124 },
  { symbol: 'USDBRL_otc', name: 'USD/BRL OTC', payout: 92, category: 'Emerging', live: true, velocity: 120 },
  { symbol: 'USDTRY_otc', name: 'USD/TRY OTC', payout: 92, category: 'Emerging', live: true, velocity: 118 },
  { symbol: 'USDMXN_otc', name: 'USD/MXN OTC', payout: 90, category: 'Emerging', live: true, velocity: 115 },

  // Commodities & Crypto
  { symbol: 'GOLD_otc', name: 'Gold OTC', payout: 90, category: 'Commodities', live: true, velocity: 110 },
  { symbol: 'SILVER_otc', name: 'Silver OTC', payout: 90, category: 'Commodities', live: true, velocity: 105 },
  { symbol: 'CRUDE_otc', name: 'Crude Oil OTC', payout: 90, category: 'Commodities', live: true, velocity: 108 },
  { symbol: 'BTCUSD', name: 'Bitcoin / USD', payout: 85, category: 'Crypto', live: false, velocity: 95 },
  { symbol: 'ETHUSD', name: 'Ethereum / USD', payout: 85, category: 'Crypto', live: false, velocity: 88 },
  { symbol: 'SOLUSD', name: 'Solana / USD', payout: 85, category: 'Crypto', live: false, velocity: 90 },
  { symbol: 'XRPUSD', name: 'Ripple / USD', payout: 85, category: 'Crypto', live: false, velocity: 86 },

  // Stocks & Indices
  { symbol: '#AAPL_otc', name: 'Apple Inc OTC', payout: 90, category: 'Stocks', live: false, velocity: 80 },
  { symbol: '#MSFT_otc', name: 'Microsoft OTC', payout: 90, category: 'Stocks', live: false, velocity: 82 },
  { symbol: '#TSLA_otc', name: 'Tesla Inc OTC', payout: 90, category: 'Stocks', live: false, velocity: 85 },
  { symbol: '#SP500_otc', name: 'S&P 500 Index OTC', payout: 90, category: 'Indices', live: false, velocity: 75 },
  { symbol: '#US100_otc', name: 'NASDAQ 100 Index OTC', payout: 90, category: 'Indices', live: false, velocity: 78 },
];
