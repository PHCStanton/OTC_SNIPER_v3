/**
 * HTTP client for Phase 2 trading endpoints.
 */

const BASE = '/api';

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);

  const res = await fetch(`${BASE}${path}`, opts);
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const msg = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

/**
 * Execute a trade.
 * @param {string} broker  - e.g. 'pocket_option'
 * @param {object} payload - { asset, amount, direction, duration, demo }
 */
export const executeTrade = (broker, payload) =>
  request('POST', `/trading/${broker}/trade`, payload);

/**
 * Fetch trade history for a broker.
 * @param {string} broker
 */
export const getTrades = (broker) => request('GET', `/trading/${broker}/trades`);

/**
 * Get broker assets.
 * @param {string} broker
 */
export const getBrokerAssets = (broker) => request('GET', `/brokers/${broker}/assets`);
