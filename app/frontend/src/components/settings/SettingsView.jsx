/**
 * SettingsView — Phase 7 settings workspace.
 * Splits Account / App / Risk concerns into dedicated panels.
 */
import { useState } from 'react';
import { ChevronRight, Database, LayoutGrid, ShieldAlert, UserRound, Zap } from 'lucide-react';
import AccountSettings from './AccountSettings.jsx';
import AppSettings from './AppSettings.jsx';
import RiskSettings from './RiskSettings.jsx';
import AISettings from './AISettings.jsx';

const TABS = [
  { id: 'account', label: 'Account', icon: UserRound, note: 'SSID, broker, session identity' },
  { id: 'app', label: 'App', icon: LayoutGrid, note: 'OTEO, ghost trading, UI prefs' },
  { id: 'ai', label: 'AI & Voice', icon: Zap, note: 'Models, reasoning profiles, voices, KB' },
  { id: 'risk', label: 'Risk', icon: ShieldAlert, note: 'Capital, payout, sizing, guardrails' },
];

export default function SettingsView() {
  const [activeTab, setActiveTab] = useState('account');

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
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
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
            </div>

            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-[#ffb800]">
              <span>Stitch Workspace</span>
              <ChevronRight size={12} />
            </div>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-3">
            {TABS.map(({ id, label, icon: Icon, note }) => {
              const selected = activeTab === id;

              return (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={`flex items-center justify-between gap-3 rounded-xl border px-4 py-4.5 text-left transition-all duration-300 ${
                    selected 
                      ? 'border-[#ffb800]/30 bg-[#ffb800]/10 text-[#ffb800] shadow-[0_0_15px_rgba(255,184,0,0.08)]' 
                      : 'border-white/5 bg-[#1e222b]/50 text-gray-400 hover:bg-[#25282f] hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${
                      selected ? 'bg-[#ffb800] text-black' : 'bg-[#25282f] text-gray-500'
                    }`}>
                      <Icon size={18} />
                    </div>
                    <div>
                      <p className="text-sm font-black uppercase tracking-wider">{label}</p>
                      <p className="mt-1 text-[10px] font-semibold tracking-normal text-inherit opacity-60 uppercase">{note}</p>
                    </div>
                  </div>
                  <ChevronRight size={14} className={selected ? 'text-[#ffb800]' : 'text-gray-600'} />
                </button>
              );
            })}
          </div>
        </header>

        <section className="animate-in fade-in duration-300">
          <ActivePanel />
        </section>
      </div>
    </div>
  );
}