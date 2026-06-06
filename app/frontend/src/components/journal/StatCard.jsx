import React from 'react';

export default function StatCard({ label, value, subValue, icon, trend, color = 'text-white' }) {
  return (
    <div className="bg-[#1a1c22] border border-white/5 rounded-xl p-5 hover:border-[#ffb800]/25 transition-all duration-300 group shadow-md hover:shadow-lg">
      <div className="flex items-start justify-between">
        <div className="p-2.5 rounded-lg bg-[#25282f] text-gray-500 group-hover:text-[#ffb800] transition-colors border border-white/5">
          {icon}
        </div>
        {trend && (
          <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded ${
            trend === 'up' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
          }`}>
            {trend === 'up' ? 'WIN' : 'LOSS'}
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-[9px] font-black text-gray-500 uppercase tracking-widest">{label}</p>
        <h2 className={`text-2xl font-black mt-1.5 leading-none ${color}`}>{value}</h2>
        <p className="text-[8px] text-gray-600 font-black mt-2 uppercase tracking-widest">{subValue}</p>
      </div>
    </div>
  );
}