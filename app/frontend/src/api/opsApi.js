/**
 * HTTP client for Phase 0 ops endpoints.
 * Chrome lifecycle + SSID session management.
 */
import { request } from './httpClient.js';

// ── Chrome lifecycle ──────────────────────────────────────────────────────────

export const chromeStart = () => request('POST', '/ops/chrome/start');
export const chromeStop = () => request('POST', '/ops/chrome/stop');
export const chromeStatus = () => request('GET', '/ops/chrome/status');

// ── Combined ops status ───────────────────────────────────────────────────────

export const opsStatus = () => request('GET', '/ops/status');

// ── Session management ────────────────────────────────────────────────────────

/**
 * Connect with an SSID.
 * @param {string} ssid  - Full 42["auth",...] frame. Pass empty string to auto-reconnect from .env.
 * @param {boolean} demo - true = demo account, false = real account.
 */
export const sessionConnect = (ssid, demo) =>
  request('POST', '/session/connect', { ssid, demo });

export const sessionDisconnect = () => request('POST', '/session/disconnect');
export const sessionStatus = () => request('GET', '/session/status');
export const sessionSsidStatus = () => request('GET', '/session/ssid-status');
export const sessionSavedSsid = (demo) => request('GET', `/session/saved-ssid?demo=${demo ? 'true' : 'false'}`);
export const sessionClearSsid = (demo) => request('POST', '/session/clear-ssid', { demo });
