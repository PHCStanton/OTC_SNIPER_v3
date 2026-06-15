/**
 * SettingsView — Phase 7 settings portal view.
 * Displays Account / App / AI / Risk settings panel.
 * Selected tab is driven globally by useLayoutStore.
 */
import AccountSettings from './AccountSettings.jsx';
import AppSettings from './AppSettings.jsx';
import RiskSettings from './RiskSettings.jsx';
import AISettings from './AISettings.jsx';
import { Database } from 'lucide-react';
import { useLayoutStore } from '../../stores/useLayoutStore.js';

export default function SettingsView() {
  const activeTab = useLayoutStore((s) => s.activeSettingsTab || 'account');

  const ActivePanel = activeTab === 'account'
    ? AccountSettings
    : activeTab === 'app'
      ? AppSettings
      : activeTab === 'ai'
        ? AISettings
        : RiskSettings;

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top,_rgba(255,184,0,0.06),_transparent_34%),linear-gradient(180deg,#0c0f0f_0%,#10151a_46%,#131820_100%)] px-4 py-4 text-[#e3e6e7] lg:px-6 lg:py-6">
      <div className="mx-auto flex max-w-[1700px] flex-col gap-6">
        <header className="rounded-[20px] border border-white/5 bg-[#1a1c22] px-6 py-5 shadow-xl">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#ffb800] text-black shadow-lg shadow-[#ffb800]/25">
              <Database size={24} />
            </div>
            <div>
              <h2 className="text-xl font-black uppercase tracking-wider text-white">Settings Portal</h2>
              <p className="mt-1 text-sm text-gray-500 font-medium">Configure network identities, algorithmic boundaries, and session guardrails.</p>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2 text-[10px] font-black uppercase tracking-widest text-gray-500">
            <span className="rounded-md border border-white/5 bg-[#25282f] px-3 py-1 text-[9px] text-gray-400">Persisted locally</span>
            <span className="rounded-md border border-white/5 bg-[#25282f] px-3 py-1 text-[9px] text-gray-400">Auth0-ready boundary</span>
            <span className="rounded-md border border-white/5 bg-[#25282f] px-3 py-1 text-[9px] text-gray-400">Fail-fast validation</span>
          </div>
        </header>

        <section className="animate-in fade-in duration-300">
          <ActivePanel />
        </section>
      </div>
    </div>
  );
}