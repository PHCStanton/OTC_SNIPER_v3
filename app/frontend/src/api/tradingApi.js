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
