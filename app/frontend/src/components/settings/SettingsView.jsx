/**
 * SettingsView — Phase 7 settings workspace.
 * Splits Account / App / Risk concerns into dedicated panels.
 */
import { useState } from 'react';
import { ChevronRight, Database, LayoutGrid, ShieldAlert, UserRound } from 'lucide-react';
import AccountSettings from './AccountSettings.jsx';
import AppSettings from './AppSettings.jsx';
import RiskSettings from './RiskSettings.jsx';

const TABS = [
  { id: 'account', label: 'Account', icon: UserRound, note: 'SSID, broker, session identity' },
  { id: 'app', label: 'App', icon: LayoutGrid, note: 'OTEO, ghost trading, UI prefs' },
  { id: 'risk', label: 'Risk', icon: ShieldAlert, note: 'Capital, payout, sizing, guardrails' },
];

export default function SettingsView() {
  const [activeTab, setActiveTab] = useState('account');

  const ActivePanel = activeTab === 'account'
    ? AccountSettings
    : activeTab === 'app'
      ? AppSettings
      : RiskSettings;

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top,_rgba(245,223,25,0.08),_transparent_34%),linear-gradient(180deg,#0c0f0f_0%,#10151a_46%,#131820_100%)] px-4 py-4 text-[#e3e6e7] lg:px-6 lg:py-6">
      <div className="mx-auto flex max-w-[1700px] flex-col gap-4">
        <header className="rounded-3xl border border-white/5 bg-[#151a22]/95 px-5 py-4 shadow-[0_15px_40px_rgba(0,0,0,0.28)]">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <div className="flex items-center gap-2">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#f5df19] text-black shadow-lg shadow-[#f5df19]/20">
                  <Database size={20} />
                </div>
                <div>
                  <h2 className="text-lg font-bold tracking-tight text-[#e3e6e7]">Settings</h2>
                  <p className="text-xs text-gray-500">Account, App, and Risk settings stay separated by design.</p>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-400">
                <span className="rounded-full border border-white/5 bg-white/5 px-3 py-1">Persisted locally</span>
                <span className="rounded-full border border-white/5 bg-white/5 px-3 py-1">Auth0-ready boundary</span>
                <span className="rounded-full border border-white/5 bg-white/5 px-3 py-1">Fail-fast validation</span>
              </div>
            </div>

            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">
              <span>Phase 7 workspace</span>
              <ChevronRight size={12} />
            </div>
          </div>

          <div className="mt-4 grid gap-2 md:grid-cols-3">
            {TABS.map(({ id, label, icon: Icon, note }) => {
              const selected = activeTab === id;

              return (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={`flex items-center justify-between gap-3 rounded-2xl border px-4 py-3 text-left transition-colors ${selected ? 'border-[#f5df19]/30 bg-[#f5df19]/10 text-[#f5df19]' : 'border-white/5 bg-[#0f1419] text-gray-400 hover:bg-white/5 hover:text-[#e3e6e7]'}`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${selected ? 'bg-[#f5df19] text-black' : 'bg-white/5 text-gray-400'}`}>
                      <Icon size={16} />
                    </div>
                    <div>
                      <p className="text-sm font-bold tracking-tight">{label}</p>
                      <p className="mt-0.5 text-[11px] font-medium tracking-normal text-inherit opacity-70">{note}</p>
                    </div>
                  </div>
                  <ChevronRight size={14} className={selected ? 'text-[#f5df19]' : 'text-gray-600'} />
                </button>
              );
            })}
          </div>
        </header>

        <section>
          <ActivePanel />
        </section>
      </div>
    </div>
  );
}