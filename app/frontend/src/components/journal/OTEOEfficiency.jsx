import React from 'react';
import { Target } from 'lucide-react';

export default function OTEOEfficiency({ ghostTrades }) {
  // Calculate win rate by score buckets
  const buckets = [
    { label: "Score 95-100", min: 95, max: 100, color: "bg-emerald-500" },
    { label: "Score 90-95", min: 90, max: 94.99, color: "bg-emerald-500/70" },
    { label: "Score 85-90", min: 85, max: 89.99, color: "bg-amber-500" },
    { label: "Score < 85", min: 0, max: 84.99, color: "bg-rose-500" },
  ];

  const stats = buckets.map(bucket => {
    const tradesInBucket = ghostTrades.filter(t => t.oteo_score >= bucket.min && t.oteo_score <= bucket.max);
    const wins = tradesInBucket.filter(t => t.outcome === 'win').length;
    const count = tradesInBucket.length;
    const winRate = count > 0 ? Math.round((wins / count) * 100) : 0;
    
    return { ...bucket, count, winRate };
  });

  return (
    <div className="bg-[#141818] border border-white/5 rounded-xl p-5">
      <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2 uppercase tracking-wider">
        <Target size={16} className="text-[#f5df19]" />
        OTEO Score Efficiency
      </h3>
      <div className="space-y-4">
        {stats.map((stat, idx) => (
          <EfficiencyRow 
            key={idx} 
            label={stat.label} 
            winRate={stat.winRate} 
            count={stat.count} 
            color={stat.color} 
          />
        ))}
      </div>
    </div>
  );
}

function EfficiencyRow({ label, winRate, count, color }) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-[10px] font-bold uppercase tracking-wider">
        <span className="text-gray-400">{label}</span>
        <span className="text-gray-200">{winRate}% <span className="text-gray-600 ml-1">({count} trades)</span></span>
      </div>
      <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
        <div 
          className={`h-full ${color} transition-all duration-1000`} 
          style={{ width: `${winRate}%` }} 
        />
      </div>
    </div>
  );
}