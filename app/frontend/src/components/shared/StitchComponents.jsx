import React, { useState } from 'react';
import { Info } from 'lucide-react';

export function SectionCard({ title, subtitle, icon: Icon, children, badge, toggle, onToggle }) {
  return (
    <section className="relative overflow-hidden rounded-[20px] bg-[#1a1c22] p-6 shadow-xl border border-white/5">
      <div className="mb-6 flex items-start justify-between">
        <div className="flex gap-4">
          {Icon && (
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#25282f] text-[#ffb800]">
              <Icon size={24} />
            </div>
          )}
          <div>
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-black uppercase tracking-wider text-white">{title}</h3>
              {badge && (
                <span className="rounded-md bg-[#ffb800]/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-[#ffb800] border border-[#ffb800]/20">
                  {badge}
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-gray-500 font-medium">{subtitle}</p>
          </div>
        </div>
        {toggle !== undefined && (
          <button
            type="button"
            onClick={() => onToggle(!toggle)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none ${
              toggle ? 'bg-[#ffb800]' : 'bg-[#2d3139]'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${
                toggle ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        )}
      </div>
      <div className="space-y-6">{children}</div>
    </section>
  );
}

export function InputGroup({ label, description, tooltip, children, layout = 'vertical' }) {
  return (
    <div className={`flex ${layout === 'horizontal' ? 'flex-row items-center justify-between' : 'flex-col space-y-2'}`}>
      <div className={layout === 'horizontal' ? 'flex-1' : ''}>
        <div className="flex items-center gap-1.5">
          <p className="text-[11px] font-black uppercase tracking-[0.15em] text-gray-400">{label}</p>
          {tooltip && <Tooltip content={tooltip} />}
        </div>
        {description && <p className="mt-1 text-[11px] font-medium text-gray-600 leading-relaxed uppercase">{description}</p>}
      </div>
      <div className={layout === 'horizontal' ? 'ml-4' : 'mt-2'}>
        {children}
      </div>
    </div>
  );
}

export function NumberInput({ value, onChange, min, suffix, icon: Icon }) {
  return (
    <div className="flex h-14 w-full items-center overflow-hidden rounded-lg bg-white shadow-inner">
      <div className="flex h-full w-12 items-center justify-center bg-gray-50 text-gray-400">
        {Icon ? <Icon size={18} /> : <span className="text-lg font-bold">#</span>}
      </div>
      <input
        type="number"
        min={min}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-full flex-1 px-4 text-xl font-black text-black outline-none"
      />
      {suffix && (
        <div className="flex h-full items-center bg-gray-100 px-4 text-[10px] font-black uppercase tracking-widest text-gray-500 border-l border-gray-200">
          {suffix}
        </div>
      )}
    </div>
  );
}

export function MiniModule({ label, active, onClick, icon: Icon, compact = false }) {
  return (
    <button
      onClick={onClick}
      className={`group relative flex flex-col items-center justify-center rounded-xl border transition-all duration-300 ${
        compact ? 'p-2.5 gap-2' : 'p-4 gap-3'
      } ${
        active
          ? 'border-[#ffb800]/30 bg-[#ffb800]/5 shadow-[0_0_20px_rgba(255,184,0,0.1)]'
          : 'border-white/5 bg-white/[0.02] hover:bg-white/[0.05]'
      }`}
    >
      <div className={`flex items-center justify-center rounded-lg transition-colors ${
        compact ? 'h-9 w-9' : 'h-12 w-12'
      } ${
        active ? 'bg-[#ffb800] text-black' : 'bg-[#25282f] text-gray-500 group-hover:text-gray-300'
      }`}>
        {Icon && <Icon size={compact ? 16 : 20} />}
      </div>
      <div className="text-center">
        <p className={`font-black uppercase tracking-widest ${
          compact ? 'text-[8.5px]' : 'text-[10px]'
        } ${active ? 'text-[#ffb800]' : 'text-gray-500 group-hover:text-gray-400'}`}>
          {label}
        </p>
        <p className={`mt-0.5 text-[7.5px] font-bold uppercase tracking-widest ${active ? 'text-[#ffb800]/60' : 'text-gray-600'}`}>
          {active ? 'Active' : 'Inactive'}
        </p>
      </div>
    </button>
  );
}


export function StitchToggle({ checked, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none ${
        checked ? 'bg-[#ffb800]' : 'bg-[#2d3139]'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

export function Tooltip({ content }) {
  const [visible, setVisible] = useState(false);

  return (
    <div
      className="relative inline-flex items-center"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      <Info size={11} className="text-gray-500 hover:text-white transition-colors cursor-help" />
      {visible && content && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-52 p-2 rounded-lg bg-slate-950/95 border border-white/10 text-[9px] font-black uppercase tracking-wider text-gray-300 shadow-2xl pointer-events-none text-center leading-normal animate-in fade-in zoom-in-95 duration-150 backdrop-blur-md">
          {content}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-950/95" />
        </div>
      )}
    </div>
  );
}
