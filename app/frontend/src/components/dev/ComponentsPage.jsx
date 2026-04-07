import React, { useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import MiniSparkline from '../trading/MiniSparkline.jsx';
import PercentageGauge from '../shared/PercentageGauge.jsx';
import OTEORing from '../trading/OTEORing.jsx';
import { Star, X, Layers3, Activity, AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react';

// --- AI SVG Icons from Ai_svg_icons.md ---

const AiInsightsChipBotIcon = ({ size = 24 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 14 14"
    fill="none"
    aria-hidden="true"
  >
    <path
      fill="currentColor"
      fillRule="evenodd"
      d="M4.52212 0.683071c-0.03699 -0.34319 -0.34519 -0.5914115 -0.68838 -0.554419 -0.36033 0.03884 -0.71756 0.080286 -1.06861 0.121014l-0.12446 0.014435C1.39347 0.408653 0.399389 1.40083 0.259108 2.65118l-0.003293 0.02934c-0.042663 0.38024 -0.086119 0.76756 -0.126488 1.1588 -0.0354292 0.34336 0.214194 0.65042 0.557549 0.68585 0.343354 0.03543 0.650414 -0.21419 0.685844 -0.55755 0.03979 -0.38563 0.0827 -0.76811 0.12554 -1.1499l0.00305 -0.02717c0.07511 -0.66944 0.6115 -1.2069 1.28328 -1.28476l0.12443 -0.01443c0.3517 -0.04081 0.70373 -0.08165 1.05868 -0.11991 0.34319 -0.03699 0.59141 -0.34519 0.55442 -0.688379Zm4.95642 0c0.03699 -0.34319 0.34519 -0.5914115 0.68836 -0.554419 0.3603 0.03884 0.7175 0.080286 1.0686 0.121014l0.1245 0.014435c1.2472 0.144552 2.2412 1.136729 2.3815 2.387079l0.0033 0.02934c0.0426 0.38012 0.0861 0.76769 0.1265 1.1588 0.0354 0.34336 -0.2142 0.65042 -0.5575 0.68585 -0.3434 0.03543 -0.6505 -0.21419 -0.6859 -0.55755 -0.0398 -0.38553 -0.0827 -0.7679 -0.1255 -1.14959l-0.0031 -0.02748c-0.0751 -0.66944 -0.6115 -1.2069 -1.2833 -1.28476l-0.1244 -0.01443c-0.3517 -0.04081 -0.7037 -0.08165 -1.0587 -0.11991 -0.34313 -0.03699 -0.59136 -0.34519 -0.55436 -0.688379Zm-2.47966 0.881439c-0.37695 0 -0.7244 0.10717 -0.97724 0.36002 -0.25285 0.25285 -0.36003 0.60029 -0.36003 0.97724s0.10718 0.7244 0.36003 0.97724c0.10339 0.10339 0.2226 0.18243 0.35318 0.23974l-0.00002 0.66912c-0.59197 0.00483 -1.19608 0.02356 -1.75177 0.09614 -0.78519 0.10255 -1.42295 0.70724 -1.53867 1.50156 -0.06256 0.42945 -0.06256 0.86343 -0.06255 1.53566v0.05317c-0.00001 0.67222 -0.00001 1.1062 0.06255 1.53566 0.11572 0.79434 0.75348 1.39904 1.53867 1.50154 0.74905 0.0978 1.58608 0.0978 2.36278 0.0978h0.02821c0.7767 0 1.61373 0 2.36279 -0.0978 0.78519 -0.1025 1.42289 -0.7072 1.53859 -1.50154 0.0626 -0.42946 0.0626 -0.86344 0.0626 -1.53567v-0.05316c0 -0.67223 0 -1.10621 -0.0626 -1.53566 -0.1157 -0.79432 -0.7534 -1.39901 -1.53859 -1.50156 -0.55577 -0.07259 -1.15996 -0.09132 -1.75201 -0.09615l0.00002 -0.66912c0.13058 -0.05731 0.24979 -0.13635 0.35318 -0.23974 0.25285 -0.25284 0.36003 -0.60029 0.36003 -0.97724s-0.10718 -0.72439 -0.36003 -0.97724c-0.25284 -0.25285 -0.60029 -0.36002 -0.97724 -0.36002Zm-1.04944 1.550181c0.16018 0 0.28994 0.12975 0.28994 0.28993s-0.12976 0.28994 -0.28994 0.28994 -0.28994 -0.12976 -0.28994 -0.28994 0.12976 -0.28993 0.28994 -0.28993Zm2.10292 0c0.16018 0 0.28994 0.12975 0.28994 0.28993s-0.12976 0.28994 -0.28994 0.28994 -0.28994 -0.12976 -0.28994 -0.28994 0.12976 -0.28993 0.28994 -0.28993Z"
      clipRule="evenodd"
    ></path>
  </svg>
);

const AiInsightsIconV2 = ({ size = 24 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 14 14"
    fill="none"
    aria-hidden="true"
  >
    <path
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M11.7336 10.9952V9.30799c0.5699 0.02387 0.8554 -0.02887 1.1986 -0.26692 0.3068 -0.21281 0.4088 -0.61411 0.3083 -0.9737 -0.9828 -3.51296 -2.508 -7.06273 -6.90456 -7.06273V12.9952h3.39763c1.10453 0 2.00003 -0.8954 2.00003 -2Z"
      strokeWidth="1"
    />
    <path
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9.86719 6.50928v0.16177"
      strokeWidth="1"
    />
    <path
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M2.92163 4.0686c0.55172 0 0.86206 -0.31034 0.86206 -0.86206s-0.31034 -0.86206 -0.86206 -0.86206 -0.86206 0.31034 -0.86206 0.86206 0.31034 0.86206 0.86206 0.86206Z"
      strokeWidth="1"
    />
    <path
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M1.46167 8.09326c0.55172 0 0.86206 -0.31034 0.86206 -0.86206s-0.31034 -0.86206 -0.86206 -0.86206c-0.551719 0 -0.862061 0.31034 -0.862061 0.86206s0.310342 0.86206 0.862061 0.86206Z"
      strokeWidth="1"
    />
    <path
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M2.15112 12.1174c0.55172 0 0.86206 -0.3103 0.86206 -0.862s-0.31034 -0.8621 -0.86206 -0.8621 -0.86206 0.3104 -0.86206 0.8621 0.31034 0.862 0.86206 0.862Z"
      strokeWidth="1"
    />
    <path
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M3.78399 3.2063h2.55195"
      strokeWidth="1"
    />
    <path
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M4.79599 5.38354h1.53995"
      strokeWidth="1"
    />
    <path
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      d="m4.6748 11.2554 0 -2.00131 -1.09536 0"
      strokeWidth="1"
    />
    <path
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M3.01398 11.2554h3.32196"
      strokeWidth="1"
    />
    <path
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M2.32398 7.23071h4.01196"
      strokeWidth="1"
    />
  </svg>
);

// --- Enhanced MultiChartCard Mock for Showcase ---
function MultiChartCardMock({ asset, isSelected, signal, manipulation, stats, regime }) {
  const [isStarred, setIsStarred] = useState(false);
  const trend = 1.25;
  const positive = trend >= 0;

  return (
    <article className={`group relative rounded-2xl border ${isSelected ? 'border-[#f5df19]/50 bg-[#282d2e]' : 'border-white/5 bg-[#212127]'} p-3 transition-all hover:border-[#f5df19]/40 cursor-pointer overflow-hidden`}>
      {/* Manipulation Pulse Overlay */}
      {manipulation && (
        <div className="absolute inset-0 bg-rose-500/5 animate-pulse pointer-events-none" />
      )}

      <div className="flex items-start justify-between gap-3 relative z-10">
        <div className="flex items-center gap-2">
          <button 
            onClick={(e) => { e.stopPropagation(); setIsStarred(!isStarred); }}
            className={`transition-colors ${isStarred ? 'text-[#f5df19]' : 'text-gray-600 hover:text-gray-400'}`}
          >
            <Star size={14} fill={isStarred ? "currentColor" : "none"} />
          </button>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-gray-500">Asset</p>
            <h4 className="text-sm font-black text-[#e3e6e7]">{asset}</h4>
          </div>
        </div>

        <button className="rounded-full p-1.5 text-gray-500 transition hover:bg-white/5 hover:text-[#e3e6e7]">
          <X size={12} />
        </button>
      </div>

      <div className="mt-2 flex items-center justify-between gap-3 relative z-10">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">Price</p>
          <p className="text-base font-black text-[#e3e6e7]">1.08425</p>
        </div>

        <div className="flex flex-col items-end gap-1">
          <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${positive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-[#fe7453]/10 text-[#fe7453]'}`}>
            {positive ? '+' : ''}{trend.toFixed(2)}%
          </span>
          {regime && (
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-white/5 text-gray-400 border border-white/5">
              {regime}
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 relative h-16 group-hover:opacity-40 transition-opacity">
        <MiniSparkline ticks={[100, 102, 101, 104, 103, 106]} />
      </div>

      {/* Hybrid Gauge Overlay (visible on hover or signal) */}
      {signal && (
        <div className="absolute inset-x-0 top-12 flex flex-col items-center justify-center pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="relative w-16 h-16">
             <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="3" className="text-white/5" />
                <circle 
                  cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="3" 
                  strokeDasharray={`${(signal.confidence / 100) * 100} 100`}
                  className={signal.direction === 'call' ? 'text-emerald-500' : 'text-[#fe7453]'}
                />
             </svg>
             <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-[10px] font-black">{signal.confidence}%</span>
             </div>
          </div>
          <span className={`text-[9px] font-bold uppercase tracking-widest ${signal.direction === 'call' ? 'text-emerald-500' : 'text-[#fe7453]'}`}>
            {signal.direction}
          </span>
        </div>
      )}

      <div className="mt-3 flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500 relative z-10">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <Layers3 size={11} />
            300
          </span>
          {stats && (
            <span className="flex items-center gap-1 text-gray-400">
              <span className="text-emerald-500">{stats.w}W</span>
              <span className="opacity-30">/</span>
              <span className="text-rose-500">{stats.l}L</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {manipulation && <AlertTriangle size={12} className="text-rose-500 animate-pulse" />}
          <span>{isSelected ? 'Selected' : 'Watching'}</span>
        </div>
      </div>
    </article>
  );
}

export default function ComponentsPage() {
  const [gaugeValue, setGaugeValue] = useState(75);
  
  // Sample tick data for MiniSparkline
  const sampleTicksUp = [100, 102, 101, 104, 103, 106, 108, 107, 110, 112, 115];
  const sampleTicksDown = [115, 112, 114, 110, 108, 109, 105, 102, 104, 100, 98];

  return (
    <div className="min-h-screen bg-[#0c0f0f] text-[#e3e6e7] p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto space-y-12">
        <header className="border-b border-white/10 pb-6 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight mb-2">Component Library</h1>
            <p className="text-gray-400">View, modify, and test UI components and design elements.</p>
          </div>
          <button 
            onClick={() => window.location.href = '/'}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-xl transition-colors border border-white/10"
          >
            <ArrowLeft size={16} />
            <span className="text-sm font-semibold">Back to App</span>
          </button>
        </header>

        {/* Section 1: AI SVG Icons */}
        <section>
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
            <span className="w-2 h-6 bg-[#f5df19] rounded-full"></span>
            AI SVG Icons
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-[#151a22] border border-white/5 rounded-2xl p-6 flex flex-col items-center justify-center gap-4">
              <div className="p-4 bg-[#f5df19]/10 text-[#f5df19] rounded-xl">
                <AiInsightsChipBotIcon size={48} />
              </div>
              <div className="text-center">
                <h3 className="font-bold">Option 1: AI Scanner Robot</h3>
                <p className="text-sm text-gray-500 mt-1">Currently in use for AI Insights</p>
              </div>
            </div>
            
            <div className="bg-[#151a22] border border-white/5 rounded-2xl p-6 flex flex-col items-center justify-center gap-4">
              <div className="p-4 bg-emerald-500/10 text-emerald-400 rounded-xl">
                <AiInsightsIconV2 size={48} />
              </div>
              <div className="text-center">
                <h3 className="font-bold">Option 2: Deepfake Tech</h3>
                <p className="text-sm text-gray-500 mt-1">Alternative design for Face/AI tech</p>
              </div>
            </div>
          </div>
        </section>

        {/* Section 2: Animated Components */}
        <section>
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
            <span className="w-2 h-6 bg-emerald-500 rounded-full"></span>
            Animated Components
          </h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Percentage Gauge */}
            <div className="bg-[#151a22] border border-white/5 rounded-2xl p-6">
              <h3 className="font-bold mb-4 text-gray-300">Percentage Gauge</h3>
              <div className="flex flex-col items-center justify-center gap-6 py-4">
                <PercentageGauge 
                  percentage={gaugeValue} 
                  size={140} 
                  color={gaugeValue > 50 ? '#10b981' : '#f43f5e'} 
                  label="Win Rate" 
                />
                
                <div className="flex items-center gap-4 w-full max-w-xs mt-4">
                  <input 
                    type="range" 
                    min="0" 
                    max="100" 
                    value={gaugeValue} 
                    onChange={(e) => setGaugeValue(Number(e.target.value))}
                    className="flex-1 accent-emerald-500"
                  />
                  <span className="text-sm font-mono bg-white/5 px-2 py-1 rounded">{gaugeValue}%</span>
                </div>
              </div>
            </div>

            {/* Mini Sparklines */}
            <div className="bg-[#151a22] border border-white/5 rounded-2xl p-6">
              <h3 className="font-bold mb-4 text-gray-300">Mini Sparklines</h3>
              <div className="space-y-6">
                <div>
                  <div className="flex justify-between text-xs text-gray-400 mb-2">
                    <span>Uptrend</span>
                    <span className="text-emerald-400">+15.0%</span>
                  </div>
                  <MiniSparkline ticks={sampleTicksUp} />
                </div>
                
                <div>
                  <div className="flex justify-between text-xs text-gray-400 mb-2">
                    <span>Downtrend</span>
                    <span className="text-rose-400">-14.8%</span>
                  </div>
                  <MiniSparkline ticks={sampleTicksDown} />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Section 3: OTEO Components */}
        <section>
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
            <span className="w-2 h-6 bg-blue-500 rounded-full"></span>
            OTEO Components
          </h2>
          <div className="bg-[#151a22] border border-white/5 rounded-2xl p-6">
             <div className="grid grid-cols-1 md:grid-cols-3 gap-8 justify-items-center py-4">
                <div className="flex flex-col items-center gap-4">
                  <div className="relative w-32 h-32">
                    <OTEORing score={85} size={128} />
                    <div className="absolute inset-0 flex items-center justify-center flex-col">
                      <span className="text-xl font-bold text-emerald-400">85</span>
                      <span className="text-[10px] text-gray-500 uppercase">Score</span>
                    </div>
                  </div>
                  <span className="text-sm text-gray-400 font-semibold">Strong Call</span>
                </div>
                
                <div className="flex flex-col items-center gap-4">
                  <div className="relative w-32 h-32">
                    <OTEORing score={50} size={128} />
                    <div className="absolute inset-0 flex items-center justify-center flex-col">
                      <span className="text-xl font-bold text-amber-400">50</span>
                      <span className="text-[10px] text-gray-500 uppercase">Score</span>
                    </div>
                  </div>
                  <span className="text-sm text-gray-400 font-semibold">Neutral</span>
                </div>
                
                <div className="flex flex-col items-center gap-4">
                  <div className="relative w-32 h-32">
                    <OTEORing score={15} size={128} />
                    <div className="absolute inset-0 flex items-center justify-center flex-col">
                      <span className="text-xl font-bold text-rose-400">15</span>
                      <span className="text-[10px] text-gray-500 uppercase">Score</span>
                    </div>
                  </div>
                  <span className="text-sm text-gray-400 font-semibold">Strong Put</span>
                </div>
             </div>
          </div>
        </section>

        {/* Section 4: Enhanced Multi-Chart Cards (NEW) */}
        <section>
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
            <span className="w-2 h-6 bg-[#f5df19] rounded-full"></span>
            Proposed Asset Card Enhancements
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="space-y-2">
              <p className="text-xs font-bold text-gray-500 uppercase px-1">1. Active Signal (Hybrid View)</p>
              <MultiChartCardMock 
                asset="EURUSD OTC" 
                signal={{ direction: 'call', confidence: 82 }}
                regime="RANGE"
              />
              <p className="text-[10px] text-gray-500 italic px-1">Hover to reveal confidence gauge overlay</p>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-bold text-gray-500 uppercase px-1">2. Manipulation Detected</p>
              <MultiChartCardMock 
                asset="GBPUSD OTC" 
                manipulation={true}
                regime="STRONG"
              />
              <p className="text-[10px] text-rose-500/70 italic px-1">Card pulses red when detector is active</p>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-bold text-gray-500 uppercase px-1">3. Session Stats & Favorites</p>
              <MultiChartCardMock 
                asset="AUDCAD OTC" 
                isSelected={true}
                stats={{ w: 12, l: 4 }}
                regime="WEAK"
              />
              <p className="text-[10px] text-gray-500 italic px-1">Star for Quick-Select, Session W/L in footer</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
