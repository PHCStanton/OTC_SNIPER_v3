/**
 * Asset catalog helpers for Data Agent UI (Phase 5).
 * Pure functions — easy to unit-test without a browser.
 */

/** Format payout for display. Unknown/null → em dash percent. */
export function formatPayoutLabel(payout) {
  if (payout === null || payout === undefined || Number.isNaN(Number(payout))) {
    return '—%';
  }
  return `${Number(payout)}%`;
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
 * Unknown payout must be null — never invent 90.
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
 * Whether a catalog item matches the payout tab filter.
 * null/unknown payouts only appear under ALL.
 */
export function matchesPayoutFilter(item, payoutFilter) {
  if (!item) return false;
  if (payoutFilter === '92%+') {
    return item.payout != null && item.payout >= 92;
  }
  if (payoutFilter === '90%+') {
    return item.payout != null && item.payout >= 90;
  }
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
];

