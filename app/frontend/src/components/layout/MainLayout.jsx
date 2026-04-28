/**
 * MainLayout — overall app shell.
 * TopBar (fixed) + LeftSidebar + main content area + RightSidebar.
 * Content area renders the active view based on useLayoutStore.
 * Phase 9: ErrorBoundary, ToastContainer, and GhostTradingBanner wired in.
 */
import TopBar from './TopBar.jsx';
import LeftSidebar from './LeftSidebar.jsx';
import RightSidebar from './RightSidebar.jsx';
import { useLayoutStore } from '../../stores/useLayoutStore.js';
import AiSessionPanel from '../ai/AiSessionPanel.jsx';
import SettingsView from '../settings/SettingsView.jsx';
import JournalView from '../journal/JournalView.jsx';
import TradingPlaceholder from '../shared/TradingPlaceholder.jsx';
import RiskPlaceholder from '../shared/RiskPlaceholder.jsx';
import ErrorBoundary from '../shared/ErrorBoundary.jsx';
import ToastContainer from '../shared/ToastContainer.jsx';
import GhostTradingWidget from '../shared/GhostTradingWidget.jsx';

export default function MainLayout() {
  const { activeView, dashboardMode } = useLayoutStore();

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#0c0f0f] text-[#e3e6e7]">
      {/* Top bar — fixed height */}
      <ErrorBoundary label="Top Bar">
        <TopBar />
      </ErrorBoundary>

      {/* Body — fills remaining height */}
      <div className="flex flex-1 overflow-hidden">
        <ErrorBoundary label="Left Sidebar">
          <LeftSidebar />
        </ErrorBoundary>

        {/* Main content */}
        <main className="flex flex-col flex-1 overflow-auto relative">
          <ErrorBoundary label="Main View">
            <ActiveView view={activeView} mode={dashboardMode} />
          </ErrorBoundary>

          {/* Floating Ghost Trading Widget */}
          <GhostTradingWidget />
        </main>

        <ErrorBoundary label="Right Sidebar">
          <RightSidebar />
        </ErrorBoundary>
      </div>

      {/* Global toast notification layer — always on top */}
      <ToastContainer />
    </div>
  );
}

function ActiveView({ view, mode }) {
  if (view === 'ai') return <AiSessionPanel />;
  if (view === 'settings') return <SettingsView />;
  if (view === 'journal') return <JournalView />;

  if (mode === 'risk') return <RiskPlaceholder />;
  return <TradingPlaceholder />;
}
