import React from 'react';

export default function StatCard({ label, value, subValue, icon, trend, color = 'text-gray-100' }) {
  return (
    <div className="bg-[#141818] border border-white/5 rounded-xl p-5 hover:border-[#f5df19]/20 transition-all group">
      <div className="flex items-start justify-between">
        <div className="p-2 rounded-lg bg-white/5 text-gray-400 group-hover:text-[#f5df19] transition-colors">
          {icon}
        </div>
        {trend && (
          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
            trend === 'up' ? 'bg-emerald-400/10 text-emerald-400' : 'bg-rose-400/10 text-rose-400'
          }`}>
            {trend === 'up' ? '↑' : '↓'}
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">{label}</p>
        <h2 className={`text-2xl font-black mt-1 ${color}`}>{value}</h2>
        <p className="text-[10px] text-gray-600 font-medium mt-1 uppercase tracking-wider">{subValue}</p>
      </div>
    </div>
  );
}