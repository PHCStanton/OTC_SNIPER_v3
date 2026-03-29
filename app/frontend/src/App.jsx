import { useEffect } from 'react';
import { useLayoutStore } from './stores/useLayoutStore.js';
import { useOpsStore } from './stores/useOpsStore.js';
import MainLayout from './components/layout/MainLayout.jsx';
import { initSocket } from './api/socketClient.js';

export default function App() {
  const dashboardMode = useLayoutStore((s) => s.dashboardMode);
  const { setChromeStatus, setSessionStatus, setBalance, setAccountType } = useOpsStore();

  // Connect Socket.IO on mount and start status polling
  useEffect(() => {
    const socket = initSocket();

    socket.on('status_update', (data) => {
      if (data.chrome) {
        setChromeStatus(data.chrome.running ? 'running' : 'stopped');
      }
      if (data.session) {
        setSessionStatus(data.session.connected ? 'connected' : 'disconnected');
        if (data.session.balance != null) setBalance(data.session.balance);
        if (data.session.account_type != null) setAccountType(data.session.account_type);
      }
    });

    // Poll every 5 seconds
    const poll = () => socket.emit('check_status');
    poll();
    const interval = setInterval(poll, 5000);

    return () => {
      clearInterval(interval);
      socket.off('status_update');
    };
  }, [setChromeStatus, setSessionStatus, setBalance, setAccountType]);

  return (
    <div className="dark" data-dashboard-mode={dashboardMode}>
      <MainLayout />
    </div>
  );
}
