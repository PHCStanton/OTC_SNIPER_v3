/**
 * Socket.IO client singleton.
 * Connects to the OTC SNIPER backend on port 8001.
 * The Vite dev proxy forwards /socket.io → http://127.0.0.1:8001.
 */
import { io } from 'socket.io-client';

let socket = null;

export function initSocket() {
  if (socket) return socket;

  socket = io({
    // In dev: Vite proxy handles /socket.io → 127.0.0.1:8001
    // In prod: same origin
    path: '/socket.io',
    transports: ['websocket', 'polling'],
    reconnectionAttempts: 10,
    reconnectionDelay: 2000,
  });

  socket.on('connect', () => {
    console.info('[Socket.IO] Connected:', socket.id);
  });

  socket.on('disconnect', (reason) => {
    console.warn('[Socket.IO] Disconnected:', reason);
  });

  socket.on('connect_error', (err) => {
    console.error('[Socket.IO] Connection error:', err.message);
  });

  return socket;
}

export function getSocket() {
  if (!socket) throw new Error('Socket not initialised — call initSocket() first');
  return socket;
}
