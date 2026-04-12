import { useEffect, useState } from 'react';
import { X, Play, Loader2, Activity, AlertTriangle, Layers3, Hash } from 'lucide-react';
import { useAIStore } from '../../stores/useAIStore.js';
import { formatAssetLabel } from './chartUtils.js';

export default function TradeDetailsModal({ trade, onClose }) {
  if (!trade) return null;

  const { sendMessage, loading: aiLoading } = useAIStore();
  const [aiAnalysisText, setAiAnalysisText] = useState('');
  const [isSynthesizing, setIsSynthesizing] = useState(false);

  useEffect(() => {
    // Scroll lock for modal
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  const rawTime = trade.created_at || trade.timestamp || trade.time;
  const time = rawTime ? new Date(Number(rawTime) * 1000).toISOString().replace("T", " ").substring(0, 19) + " UTC" : '—';
  const asset = formatAssetLabel(trade.asset || trade.symbol || '—');
  const direction = (trade.direction || '').toUpperCase();
  const outcome = (trade.outcome || trade.status || 'recorded').toUpperCase();
  const pnl = Number(trade.payout ?? trade.profit ?? trade.pnl ?? 0);
  const amount = Number(trade.amount || 0);

  const context = trade.entry_context || {};
  const market = context.market_context || {};

  const oteoScore = context.oteo_score || 0;
  const zScore = context.z_score || 0;
  const velocity = context.velocity || 0;
  const adx = market.adx || 0;

  const isManualLive = trade.kind === 'live' && oteoScore === 0;

  async function handleAIAnalysis() {
    if (aiLoading) return;
    try {
      const prompt = isManualLive
        ? `Analyze this manual LIVE trade setup.
Asset: ${asset}
Direction: ${direction}
Outcome: ${outcome}
Entry PnL: ${pnl}

This was a manually executed LIVE trade with no deterministic signal attached. Provide a brief analysis purely on the context of typical manual intervention, why such a trade might have resulted in a ${outcome}, and general advice for manual trading in the current broader market regime. Address it as an actionable insight.`
        : `Analyze this specific deterministic trade setup.
Asset: ${asset}
Direction: ${direction}
Outcome: ${outcome}
Entry PnL: ${pnl}
OTEO Score: ${oteoScore.toFixed(1)}
Z-Score: ${zScore.toFixed(2)}
Velocity: ${velocity.toExponential(2)}
ADX: ${adx.toFixed(2)}
Market Regime: ${market.adx_regime || 'Unknown'}

Provide a brief analysis on why this exact momentum and context resulted in a ${outcome}, and if the setup expiry was appropriate. Address it as an actionable insight.`;

      const response = await sendMessage({ text: prompt, model: 'grok-4-1-fast-non-reasoning' });
      if (response && response.response) {
        setAiAnalysisText(response.response);
      }
    } catch (err) {
      console.error("AI Analysis failed", err);
      setAiAnalysisText(`Analysis Failed: ${err.message}`);
    }
  }

  function handleVoicePlay() {
    if (!aiAnalysisText || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(aiAnalysisText);
    utterance.rate = 1.05;
    utterance.onstart = () => setIsSynthesizing(true);
    utterance.onend = () => setIsSynthesizing(false);
    utterance.onerror = () => setIsSynthesizing(false);
    window.speechSynthesis.speak(utterance);
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="flex w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#151a22] shadow-2xl shadow-black/50 max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 bg-[#11181c] p-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-white/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                {trade.kind === 'ghost' ? 'Ghost Trade' : 'Live Trade'}
              </span>
              <span className="text-xs text-gray-400">{time}</span>
            </div>
            <h2 className="mt-1 text-xl font-black text-[#e3e6e7]">{asset} • {direction}</h2>
          </div>
          <button onClick={onClose} className="rounded-full bg-white/5 p-2 text-gray-400 transition hover:bg-white/10 hover:text-white">
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          
          {/* Main Results */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="rounded-xl border border-white/5 bg-[#1a1717] p-3 text-center">
              <p className="text-[10px] font-semibold uppercase text-gray-500">Outcome</p>
              <p className={`mt-1 text-lg font-bold ${outcome === 'WIN' ? 'text-emerald-400' : outcome === 'LOSS' ? 'text-red-400' : 'text-gray-300'}`}>
                {outcome}
              </p>
            </div>
            <div className="rounded-xl border border-white/5 bg-[#1a1717] p-3 text-center">
              <p className="text-[10px] font-semibold uppercase text-gray-500">Risked</p>
              <p className="mt-1 text-lg font-bold text-gray-300">${amount.toFixed(2)}</p>
            </div>
            <div className="rounded-xl border border-white/5 bg-[#1a1717] p-3 text-center">
              <p className="text-[10px] font-semibold uppercase text-gray-500">Return</p>
              <p className={`mt-1 text-lg font-bold ${pnl > 0 ? 'text-emerald-400' : pnl < 0 ? 'text-red-400' : 'text-gray-500'}`}>
                {pnl > 0 ? '+' : ''}${Math.abs(pnl).toFixed(2)}
              </p>
            </div>
            <div className="rounded-xl border border-white/5 bg-[#1a1717] p-3 text-center">
              <p className="text-[10px] font-semibold uppercase text-gray-500">OTEO Score</p>
              <p className="mt-1 text-lg font-bold text-[#f5df19]">
                {isManualLive ? 'N/A' : oteoScore.toFixed(1)}
              </p>
            </div>
          </div>

          {/* Deep Metadata */}
          <div className="rounded-xl border border-white/5 bg-[#1a1717] p-4 text-xs">
            <h3 className="mb-3 flex items-center gap-1.5 font-bold uppercase tracking-wider text-gray-400 border-b border-white/5 pb-2">
              <Layers3 size={14} /> Trade Context & Metrics
            </h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              <div className="flex justify-between">
                <span className="text-gray-500">Z-Score:</span>
                <span className="text-gray-300 font-mono">{zScore.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Velocity:</span>
                <span className="text-gray-300 font-mono">{velocity.toExponential(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">ADX:</span>
                <span className="text-gray-300 font-mono">{adx.toFixed(2)} ({market.adx_regime || 'N/A'})</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Manipulated:</span>
                <span className="text-gray-300 font-mono">{context.manipulation?.detected ? 'YES' : 'NO'}</span>
              </div>
              <div className="flex justify-between col-span-2 mt-2 pt-2 border-t border-white/5">
                <span className="text-gray-500">Session ID:</span>
                <span className="text-gray-500 font-mono text-[10px] truncate max-w-[200px]">{trade.session_id}</span>
              </div>
            </div>
          </div>

          {/* AI Analysis Block */}
          <div className="rounded-xl border border-[#f5df19]/20 bg-[#11181c] overflow-hidden">
            <div className="flex items-center justify-between border-b border-[#f5df19]/10 bg-[#1a1717] px-4 py-3">
              <div className="flex items-center gap-2">
                <div className="text-[#f5df19]">
                   <AiChipIcon size={16} />
                </div>
                <h3 className="text-xs font-black uppercase tracking-wider text-[#e3e6e7]">AI Analysis</h3>
              </div>
              <button
                onClick={handleAIAnalysis}
                disabled={aiLoading}
                className="flex items-center gap-1.5 rounded-full border border-[#f5df19]/30 bg-[#f5df19]/10 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[#f5df19] transition-colors hover:bg-[#f5df19]/20 disabled:opacity-50"
              >
                {aiLoading ? <Loader2 size={12} className="animate-spin" /> : <Activity size={12} />}
                {aiAnalysisText ? 'Re-Analyze' : 'Run Analysis'}
              </button>
            </div>
            
            {aiAnalysisText && (
              <div className="flex flex-col gap-2 p-4">
                <p className="whitespace-pre-wrap text-[11px] leading-relaxed text-gray-300">
                  {aiAnalysisText}
                </p>
                <div className="flex justify-end mt-2">
                  <button 
                    onClick={handleVoicePlay} 
                    className={`flex items-center gap-1 rounded bg-[#212127] px-2 py-1 text-[10px] font-bold text-gray-400 hover:text-white ${isSynthesizing ? 'text-[#f5df19]' : ''}`}
                  >
                    <Play size={10} className={isSynthesizing ? 'text-[#f5df19]' : ''} />
                    {isSynthesizing ? 'PLAYING...' : 'PLAY AUDIO'}
                  </button>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}

function AiChipIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="chipBodyGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#334155" />
          <stop offset="100%" stopColor="#0f172a" />
        </linearGradient>
        <filter id="chipGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
      <rect x="32" y="2" width="4" height="12" rx="1" fill="#94a3b8" />
      <rect x="48" y="0" width="4" height="14" rx="1" fill="#f5df19" />
      <rect x="64" y="2" width="4" height="12" rx="1" fill="#94a3b8" />
      <rect x="32" y="86" width="4" height="12" rx="1" fill="#94a3b8" />
      <rect x="48" y="86" width="4" height="14" rx="1" fill="#f5df19" />
      <rect x="64" y="86" width="4" height="12" rx="1" fill="#94a3b8" />
      <rect x="2" y="32" width="12" height="4" rx="1" fill="#94a3b8" />
      <rect x="0" y="48" width="14" height="4" rx="1" fill="#f5df19" />
      <rect x="2" y="64" width="12" height="4" rx="1" fill="#94a3b8" />
      <rect x="86" y="32" width="12" height="4" rx="1" fill="#94a3b8" />
      <rect x="86" y="48" width="14" height="4" rx="1" fill="#f5df19" />
      <rect x="86" y="64" width="12" height="4" rx="1" fill="#94a3b8" />
      <rect x="12" y="12" width="76" height="76" rx="8" fill="url(#chipBodyGradient)" stroke="#1e293b" strokeWidth="2" />
      <rect x="18" y="18" width="64" height="64" rx="6" fill="none" stroke="#f5df19" strokeWidth="0.5" opacity="0.3" />
      <rect x="28" y="28" width="44" height="44" rx="4" fill="#1e293b" opacity="0.5" />
      <text x="50" y="52" fontFamily="system-ui, sans-serif" fontSize="42" fontWeight="900" fill="#f5df19" textAnchor="middle" dominantBaseline="central" filter="url(#chipGlow)" style={{ letterSpacing: '-0.02em' }}>AI</text>
      <circle cx="18" cy="18" r="1.5" fill="#f5df19" opacity="0.5" />
      <circle cx="82" cy="18" r="1.5" fill="#f5df19" opacity="0.5" />
      <circle cx="18" cy="82" r="1.5" fill="#f5df19" opacity="0.5" />
      <circle cx="82" cy="82" r="1.5" fill="#f5df19" opacity="0.5" />
    </svg>
  );
}
