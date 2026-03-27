/**
 * MainLayout — overall app shell.
 * TopBar (fixed) + LeftSidebar + main content area + RightSidebar.
 * Content area renders the active view based on useLayoutStore.
 */
import TopBar from './TopBar.jsx';
import LeftSidebar from './LeftSidebar.jsx';
import RightSidebar from './RightSidebar.jsx';
import { useLayoutStore } from '../../stores/useLayoutStore.js';
import TradingPlaceholder from '../shared/TradingPlaceholder.jsx';
import RiskPlaceholder from '../shared/RiskPlaceholder.jsx';

export default function MainLayout() {
  const { activeView, dashboardMode } = useLayoutStore();

  return (
    <div className="flex flex-col h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 overflow-hidden">
      {/* Top bar — fixed height */}
      <TopBar />

      {/* Body — fills remaining height */}
      <div className="flex flex-1 overflow-hidden">
        <LeftSidebar />

        {/* Main content */}
        <main className="flex-1 overflow-auto">
          <ActiveView view={activeView} mode={dashboardMode} />
        </main>

        <RightSidebar />
      </div>
    </div>
  );
}

function ActiveView({ view, mode }) {
  // Settings and journal are view-specific; trading/risk follow dashboardMode
  if (view === 'settings') return <SettingsPlaceholder />;
  if (view === 'journal') return <JournalPlaceholder />;

  // Default: show trading or risk based on dashboardMode
  if (mode === 'risk') return <RiskPlaceholder />;
  return <TradingPlaceholder />;
}

function SettingsPlaceholder() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center text-slate-400">
        <p className="text-lg font-semibold">Settings</p>
        <p className="text-sm mt-1">Phase 7 — Coming soon</p>
      </div>
    </div>
  );
}

function JournalPlaceholder() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center text-slate-400">
        <p className="text-lg font-semibold">Journal</p>
        <p className="text-sm mt-1">Phase 8 — Coming soon</p>
      </div>
    </div>
  );
}
