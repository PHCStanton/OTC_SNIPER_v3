/**
 * Socket.IO helpers for Phase 3 streaming events.
 * Uses the shared socket singleton from socketClient.js.
 */
import { getSocket } from './socketClient.js';

/**
 * Subscribe to a single asset's tick stream.
 * @param {string} asset
 */
export function focusAsset(asset) {
  getSocket().emit('focus_asset', { asset });
}

/**
 * Subscribe to multiple assets (multi-chart mode, max 9).
 * @param {string[]} assets
 */
export function watchAssets(assets) {
  getSocket().emit('watch_assets', { assets });
}

export function updateAllowedAssets(assets) {
  getSocket().emit('update_allowed_assets', { assets });
}

/**
 * Register a handler for incoming tick/signal data.
 * @param {function} handler - called with { asset, ticks, signal, manipulation }
 * @returns {function} unsubscribe
 */
export function onMarketData(handler) {
  const socket = getSocket();
  socket.on('market_data', handler);
  return () => socket.off('market_data', handler);
}

/**
 * Register a handler for signal events.
 * @param {function} handler
 * @returns {function} unsubscribe
 */
export function onSignal(handler) {
  const socket = getSocket();
  socket.on('signal', handler);
  return () => socket.off('signal', handler);
}
