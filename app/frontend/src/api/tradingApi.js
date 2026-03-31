/**
 * HTTP client for Phase 2 trading endpoints.
 */
import { request } from './httpClient.js';

/**
 * Execute a trade.
 * @param {string} broker  - e.g. 'pocket_option'
 * @param {object} payload - { asset, amount, direction, duration, demo }
 */
export const executeTrade = (broker, payload) =>
  request('POST', `/brokers/${broker}/trade`, payload);

/**
 * Fetch trade history for a broker.
 * @param {string} broker
 * @param {string} sessionId
 * @param {number} [limit=50]
 */
export const getTrades = (broker, sessionId, limit = 50) => {
  if (!sessionId) {
    throw new Error('sessionId is required to load trade history.');
  }

  const params = new URLSearchParams({ session_id: sessionId, limit: String(limit) });
  return request('GET', `/brokers/${broker}/trades?${params.toString()}`);
};

/**
 * Get broker assets.
 * @param {string} broker
 */
export const getBrokerAssets = (broker) => request('GET', `/brokers/${broker}/assets`);
