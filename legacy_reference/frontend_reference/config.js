/**
 * App Configuration
 * Centralised URL config for Backend API, WebSocket, and Streaming server.
 * Override at runtime with Vite env vars:
 *   VITE_API_URL, VITE_WS_URL, VITE_STREAM_URL
 */
export const API_URL    = import.meta.env.VITE_API_URL    || 'http://localhost:8001/api';
export const WS_URL     = import.meta.env.VITE_WS_URL     || 'ws://localhost:8001/ws';
export const STREAM_URL = import.meta.env.VITE_STREAM_URL || 'http://localhost:3001';
