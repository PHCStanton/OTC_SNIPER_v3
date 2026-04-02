import { useEffect } from 'react';
import { initSocket } from './api/socketClient.js';
import { useStreamConnection } from './hooks/useStreamConnection.js';
import { useLayoutStore } from './stores/useLayoutStore.js';
import { useOpsStore } from './stores/useOpsStore.js';
import { useRiskStore } from './stores/useRiskStore.js';
import { useToastStore } from './stores/useToastStore.js';
import { useTradingStore } from './stores/useTradingStore.js';
import MainLayout from './components/layout/MainLayout.jsx';
import ErrorBoundary from './components/shared/ErrorBoundary.jsx';
import ComponentsPage from './components/dev/ComponentsPage.jsx';

const VALID_TRADE_OUTCOMES = new Set(['win', 'loss', 'void']);

export default function App() {
  const dashboardMode = useLayoutStore((s) => s.dashboardMode);
  const { setChromeStatus, setSessionStatus, setSessionId, setBalance, setAccountType } = useOpsStore();

  useStreamConnection();

  // Connect Socket.IO on mount and start status polling
  useEffect(() => {
    const socket = initSocket();

    socket.on('status_update', (data) => {
      if (data.chrome) {
        setChromeStatus(data.chrome.running ? 'running' : 'stopped');
      }
      if (data.session) {
        setSessionStatus(data.session.connected ? 'connected' : 'disconnected');
        setSessionId(data.session.session_id ?? null);
        if (data.session.balance != null) setBalance(data.session.balance);
        if (data.session.account_type != null) setAccountType(data.session.account_type);
      }
    });

    socket.on('trade_result', (data) => {
      const outcome = typeof data?.outcome === 'string' ? data.outcome.trim().toLowerCase() : '';
      if (!VALID_TRADE_OUTCOMES.has(outcome)) {
        useTradingStore.getState().setLastTradeResult(data);
        useToastStore.getState().addToast({ type: 'info', message: 'Trade result received.' });
        return;
      }

      const profit = Number(data?.profit);
      const stake = Number(data?.amount ?? 0);
      const pnl = Number.isFinite(profit) ? profit : 0;

      useTradingStore.getState().setLastTradeResult({
        ...data,
        outcome,
        pnl,
      });

      useRiskStore.getState().recordTradeResult({
        outcome,
        pnl,
        stake,
        payoutPercentage: data?.payout_pct,
        source: 'live',
      });

      const pnlLabel = pnl > 0 ? `+$${pnl.toFixed(2)}` : pnl < 0 ? `-$${Math.abs(pnl).toFixed(2)}` : '$0.00';
      if (outcome === 'win') {
        useToastStore.getState().addToast({ type: 'success', message: `WIN — ${pnlLabel}` });
      } else if (outcome === 'loss') {
        useToastStore.getState().addToast({ type: 'error', message: `LOSS — ${pnlLabel}` });
      } else {
        useToastStore.getState().addToast({ type: 'warning', message: 'Trade recorded as VOID.' });
      }
    });

    // Poll every 5 seconds
    const poll = () => socket.emit('check_status');
    poll();
    const interval = setInterval(poll, 5000);

    return () => {
      clearInterval(interval);
      socket.off('status_update');
      socket.off('trade_result');
    };
  }, [setChromeStatus, setSessionStatus, setSessionId, setBalance, setAccountType]);

  return (
    <div className="dark" data-dashboard-mode={dashboardMode}>
      <ErrorBoundary label="Application">
        {window.location.pathname === '/components' ? <ComponentsPage /> : <MainLayout />}
      </ErrorBoundary>
    </div>
  );
}
