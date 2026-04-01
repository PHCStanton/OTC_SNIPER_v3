/**
 * Socket.IO client singleton.
 * Connects to the OTC SNIPER backend on port 8001.
 * The Vite dev proxy forwards /socket.io → http://127.0.0.1:8001.
 */
import { io } from 'socket.io-client';

let socket = null;

function resolveSocketUrl() {
  const configured = import.meta.env.VITE_SOCKET_URL;
  if (typeof configured === 'string' && configured.trim().length > 0) {
    return configured.trim();
  }

  const { protocol, hostname, port } = window.location;
  const isViteDevPort = port === '5173' || port === '5174' || port === '5175';
  if (isViteDevPort) {
    const backendProtocol = protocol === 'https:' ? 'https:' : 'http:';
    return `${backendProtocol}//${hostname}:8001`;
  }

  return undefined;
}

export function initSocket() {
  if (socket) return socket;

  socket = io(resolveSocketUrl(), {
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
