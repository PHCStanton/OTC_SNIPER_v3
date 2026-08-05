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
