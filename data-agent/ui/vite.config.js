import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3001,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
        // Critical for SSE: disable proxy response buffering so ticks stream immediately
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes, req) => {
            const url = req.url || '';
            if (url.includes('/stream')) {
              // Prevent Node/http-proxy from buffering event-stream chunks
              proxyRes.headers['cache-control'] = 'no-cache, no-transform';
              proxyRes.headers['x-accel-buffering'] = 'no';
              // Ensure connection stays open for EventSource
              proxyRes.headers['connection'] = 'keep-alive';
            }
          });
        },
      },
    },
  },
});
